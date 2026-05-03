from __future__ import annotations

import json
import os
import queue
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import threading

from llmchatflow.core.memory.storage import MemoryStore
from .faiss_helper import FaissIndex
import logging

logger = logging.getLogger(__name__)


class SQLiteFaissMemoryStore(MemoryStore):
    def __init__(
        self,
        db_path: str = "memory.db",
        faiss_index_path: Optional[str] = None,
        embedding_dim: Optional[int] = None,
    ):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._faiss_index_path = faiss_index_path or (db_path + ".faiss")
        self._embedding_dim = int(embedding_dim) if embedding_dim else None
        self._faiss: Optional[FaissIndex] = None
        self._faiss_lock = threading.Lock()
        self._global_lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._batch_size = 5  # TODO: expose to config
        self._pending_ops = 0
        self._faiss_queue: "queue.Queue[Tuple[str, int, List[float]]]" = queue.Queue()
        self._faiss_stop = threading.Event()
        self._faiss_worker_thread = threading.Thread(target=self._faiss_worker, daemon=True)
        self._ensure_tables()
        self._ensure_faiss()
        self._faiss_worker_thread.start()

    def _faiss_worker(self) -> None:
        while not self._faiss_stop.is_set():
            try:
                item = self._faiss_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            batch: List[Tuple[str, int, List[float]]] = [item]
            try:
                while len(batch) < 128:
                    batch.append(self._faiss_queue.get_nowait())
            except queue.Empty:
                pass

            if self._faiss is None:
                continue

            ids = [faiss_id for _, faiss_id, _ in batch]
            vecs = [vec for _, _, vec in batch]
            try:
                with self._faiss_lock:
                    self._faiss.add(ids, vecs, normalize=True)
            except Exception as e:
                logger.warning("FAISS async add failed (%s)", str(e))
                continue

            with self._global_lock:
                try:
                    if not self._conn.in_transaction:
                        self._conn.execute("BEGIN")
                    cur = self._conn.cursor()
                    cur.executemany(
                        "UPDATE faiss_vectors SET faiss_dirty=0 WHERE faiss_id=?",
                        [(int(i),) for i in ids],
                    )
                    self._conn.commit()
                except Exception:
                    self._conn.rollback()
                    raise

    def _ensure_tables(self):
        with self._global_lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS kv (
                    k TEXT PRIMARY KEY,
                    v TEXT NOT NULL
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS session (
                    session_id TEXT PRIMARY KEY,
                    owner_id TEXT,
                    timestamp INTEGER,
                    mode TEXT,
                    memory_policy TEXT,
                    metadata TEXT
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_session_owner ON session(owner_id)")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS session_participants (
                    uuid TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    participant_id TEXT NOT NULL,
                    role TEXT NOT NULL
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sp_session ON session_participants(session_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sp_participant ON session_participants(participant_id)")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS memory (
                    uuid TEXT PRIMARY KEY,
                    turn_id TEXT,
                    user_id TEXT,
                    session_id TEXT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    memory_scope TEXT NOT NULL,
                    importance INTEGER NOT NULL,
                    decay_rate REAL NOT NULL,
                    timestamp INTEGER NOT NULL,
                    metadata TEXT
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_session_time ON memory(session_id, timestamp)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_user ON memory(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_turn ON memory(turn_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON memory(memory_type)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_scope ON memory(memory_scope)")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS faiss_vectors (
                    uuid TEXT PRIMARY KEY,
                    faiss_id INTEGER NOT NULL UNIQUE,
                    embedding TEXT NOT NULL,
                    faiss_dirty INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_faiss_vectors_dirty ON faiss_vectors(faiss_dirty)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_faiss_vectors_faiss_id ON faiss_vectors(faiss_id)")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS faiss_kv (
                    k TEXT PRIMARY KEY,
                    v TEXT NOT NULL
                )
                """
            )
            self._conn.commit()
    
    def _get_kv(self, key: str) -> Optional[str]:
        cur = self._conn.cursor()
        cur.execute("SELECT v FROM kv WHERE k=?", (key,))
        row = cur.fetchone()
        return str(row[0]) if row else None

    def _set_kv(self, key: str, value: str) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO kv(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
            (key, value),
        )

    def _faiss_get_kv(self, key: str) -> Optional[str]:
        cur = self._conn.cursor()
        cur.execute("SELECT v FROM faiss_kv WHERE k=?", (key,))
        row = cur.fetchone()
        return str(row[0]) if row else None

    def _faiss_set_kv(self, key: str, value: str) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO faiss_kv(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
            (key, value),
        )

    def _allocate_faiss_id_locked(self) -> int:
        raw = self._faiss_get_kv("next_faiss_id")
        if raw is None:
            self._faiss_set_kv("next_faiss_id", "1")
            return 0
        current = int(raw)
        self._faiss_set_kv("next_faiss_id", str(current + 1))
        return current

    def _ensure_faiss(self) -> None:
        if self._faiss is not None:
            return
        dim = self._embedding_dim
        if dim is None:
            with self._global_lock:
                stored = self._get_kv("embedding_dim")
            if stored:
                dim = int(stored)
                self._embedding_dim = dim
        if dim is None:
            return
        try:
            self._faiss = FaissIndex(self._faiss_index_path, dim)
        except ImportError as e:
            logger.warning("FAISS is not available, vector search will be disabled (%s)", str(e))
            self._faiss = None

    def _ensure_faiss_dim(self, embedding: Sequence[float]) -> None:
        if self._embedding_dim is None:
            with self._global_lock:
                try:
                    if not self._conn.in_transaction:
                        self._conn.execute("BEGIN")
                    self._embedding_dim = int(len(embedding))
                    self._set_kv("embedding_dim", str(self._embedding_dim))
                    self._pending_ops_main = getattr(self, "_pending_ops_main", 0) + 1
                    if self._pending_ops_main >= self._batch_size:
                        self._conn.commit()
                        self._pending_ops_main = 0
                except Exception:
                    self._conn.rollback()
                    self._pending_ops_main = 0
                    raise
        self._ensure_faiss()

    def insert_memory(
        self,
        session_id: str,
        role: str,
        content: str,
        embedding: List[float],
        importance: float,
        timestamp: Optional[int] = None,
        user_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        memory_type: str = "episodic",
        memory_scope: str = "session",
        decay_rate: float = 0.1,
    ) -> str:
        ts = int(timestamp if timestamp is not None else time.time())
        self._ensure_faiss_dim(embedding)
        embedding_json = json.dumps(list(embedding))
        mem_uuid = str(uuid.uuid4())

        with self._global_lock:
            try:
                if not self._conn.in_transaction:
                    self._conn.execute("BEGIN")
                cur = self._conn.cursor()
                faiss_id = int(self._allocate_faiss_id_locked())
                cur.execute(
                    """
                    INSERT INTO memory(
                        uuid, turn_id, user_id, session_id, role, content, memory_type, memory_scope,
                        importance, decay_rate, timestamp, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mem_uuid,
                        turn_id,
                        user_id,
                        session_id,
                        role,
                        content,
                        memory_type,
                        memory_scope,
                        int(round(float(importance) * 100.0)),
                        decay_rate,
                        int(ts),
                        "{}",
                    ),
                )
                cur.execute(
                    "INSERT INTO faiss_vectors(uuid, faiss_id, embedding, faiss_dirty) VALUES (?, ?, ?, 1)",
                    (mem_uuid, faiss_id, embedding_json),
                )
                self._pending_ops_main = getattr(self, "_pending_ops_main", 0) + 1
                if self._pending_ops_main >= self._batch_size:
                    self._conn.commit()
                    self._pending_ops_main = 0
            except Exception:
                self._conn.rollback()
                self._pending_ops_main = 0
                raise

        with self._global_lock:
            try:
                self._faiss_queue.put_nowait((mem_uuid, faiss_id, list(embedding)))
            except queue.Full:
                pass
        return mem_uuid

    def rebuild_faiss(self, max_batch: int = 2000) -> int:
        with self._global_lock:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT uuid, faiss_id, embedding FROM faiss_vectors WHERE faiss_dirty=1 ORDER BY rowid ASC LIMIT ?",
                (int(max_batch),),
            )
            rows = cur.fetchall()
        if not rows:
            return 0
        enqueued = 0
        for uuid_str, faiss_id, emb_json in rows:
            try:
                emb = json.loads(emb_json)
                if not isinstance(emb, list):
                    continue
                with self._global_lock:
                    try:
                        self._faiss_queue.put_nowait((str(uuid_str), int(faiss_id), [float(x) for x in emb]))
                        enqueued += 1
                    except queue.Full:
                        break
            except Exception:
                continue
        return enqueued

    def insert_message(
        self,
        session_id: str,
        role: str,
        text: str,
        embedding: List[float],
        importance: float,
        timestamp: int,
        user_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        memory_type: str = "episodic",
        memory_scope: str = "session",
        decay_rate: float = 0.1,
    ) -> None:
        self.insert_memory(
            session_id=session_id,
            role=role,
            content=text,
            embedding=embedding,
            importance=importance,
            timestamp=timestamp,
            user_id=user_id,
            turn_id=turn_id,
            memory_type=memory_type,
            memory_scope=memory_scope,
            decay_rate=decay_rate,
        )

    def fetch_messages_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        with self._global_lock:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT role, content, importance, timestamp, memory_type FROM memory WHERE session_id=? ORDER BY timestamp ASC",
                (session_id,),
            )
            rows = cur.fetchall()
        result: List[Dict[str, Any]] = []
        for role, content, importance, ts, memory_type in rows:
            result.append(
                {
                    "role": role,
                    "text": content,
                    "importance": float(importance) / 100.0,
                    "timestamp": int(ts),
                    "memory_type": str(memory_type),
                }
            )
        return result

    def fetch_memories_by_uuids(self, uuids: Sequence[str]) -> List[Dict[str, Any]]:
        if not uuids:
            return []
        placeholders = ",".join(["?"] * len(uuids))
        with self._global_lock:
            cur = self._conn.cursor()
            cur.execute(
                f"SELECT uuid, turn_id, user_id, session_id, role, content, memory_type, memory_scope, importance, decay_rate, timestamp, metadata FROM memory WHERE uuid IN ({placeholders})",
                tuple(str(x) for x in uuids),
            )
            rows = cur.fetchall()
        by_id: Dict[str, Dict[str, Any]] = {}
        for (
            uuid_str,
            turn_id,
            user_id,
            session_id,
            role,
            content,
            memory_type,
            memory_scope,
            importance,
            decay_rate,
            ts,
            metadata_json,
        ) in rows:
            by_id[str(uuid_str)] = {
                "id": str(uuid_str),
                "uuid": str(uuid_str),
                "turn_id": turn_id,
                "user_id": user_id,
                "session_id": str(session_id),
                "role": str(role),
                "text": str(content),
                "memory_type": str(memory_type),
                "memory_scope": str(memory_scope),
                "importance": float(importance) / 100.0,
                "decay_rate": float(decay_rate),
                "timestamp": int(ts),
                "metadata": json.loads(metadata_json) if metadata_json else {},
            }
        return [by_id[str(x)] for x in uuids if str(x) in by_id]

    def search_records(
        self,
        session_id: str,
        query_embedding: Sequence[float],
        top_k: int,
        filter_strategy: str = "global",
        oversample: int = 5,
    ) -> List[Dict[str, Any]]:
        self._ensure_faiss_dim(query_embedding)
        if self._faiss is None:
            return []
        want = int(top_k)
        k = max(want, want * int(oversample))
        with self._faiss_lock:
            result = self._faiss.search(query_embedding, k, normalize=True)
        faiss_ids = [int(x) for x in result.ids.tolist() if int(x) != -1]
        scores = [float(x) for x in result.scores.tolist() if x is not None]
        if not faiss_ids:
            return []

        selected_ids: List[int] = []
        selected_scores: List[float] = []
        if filter_strategy == "session_based":
            with self._global_lock:
                placeholders = ",".join(["?"] * len(faiss_ids))
                cur = self._conn.cursor()
                cur.execute(
                    f"SELECT fv.faiss_id FROM faiss_vectors fv JOIN memory m ON m.uuid=fv.uuid WHERE m.session_id=? AND fv.faiss_id IN ({placeholders})",
                    (session_id, *[int(x) for x in faiss_ids]),
                )
                allowed = {int(r[0]) for r in cur.fetchall()}
            for i, mid in enumerate(faiss_ids):
                if mid in allowed:
                    selected_ids.append(mid)
                    selected_scores.append(scores[i] if i < len(scores) else 0.0)
                    if len(selected_ids) >= want:
                        break
        else:
            selected_ids = faiss_ids[:want]
            selected_scores = scores[:want]

        with self._global_lock:
            placeholders = ",".join(["?"] * len(selected_ids)) if selected_ids else "?"
            cur = self._conn.cursor()
            cur.execute(
                f"SELECT uuid, faiss_id FROM faiss_vectors WHERE faiss_id IN ({placeholders})",
                tuple(int(x) for x in selected_ids) if selected_ids else (-1,),
            )
            id_to_uuid = {int(fid): str(u) for (u, fid) in cur.fetchall()}
        selected_uuids = [id_to_uuid.get(int(fid), "") for fid in selected_ids]
        selected_uuids = [u for u in selected_uuids if u]

        records = self.fetch_memories_by_uuids(selected_uuids)
        by_id = {str(r["id"]): r for r in records}
        out: List[Dict[str, Any]] = []
        for i, fid in enumerate(selected_ids):
            uuid_str = id_to_uuid.get(int(fid))
            if not uuid_str:
                continue
            r = by_id.get(str(uuid_str))
            if not r:
                continue
            r["similarity"] = max(0.0, float(selected_scores[i] if i < len(selected_scores) else 0.0))
            out.append(r)
        return out
