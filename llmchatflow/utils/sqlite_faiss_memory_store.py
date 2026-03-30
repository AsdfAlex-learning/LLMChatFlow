from __future__ import annotations

import json
import os
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
        self._main_thread_id = threading.get_ident()
        self._main_conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._main_conn.execute("PRAGMA journal_mode=WAL;")
        self._main_conn.execute("PRAGMA synchronous=NORMAL;")
        self._tls = threading.local()
        self._batch_size = 5  # TODO: expose to config
        self._tx_counts: Dict[int, int] = {}
        self._tx_active: Dict[int, bool] = {}
        self._ensure_tables()
        self._ensure_faiss()

    def _get_conn(self) -> sqlite3.Connection:
        tid = threading.get_ident()
        if tid == self._main_thread_id:
            return self._main_conn
        conn = getattr(self._tls, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            self._tls.conn = conn
        return conn

    def _ensure_tables(self):
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT NOT NULL UNIQUE,
                turn_id TEXT,
                user_id TEXT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL DEFAULT 'episodic',
                importance REAL NOT NULL,
                timestamp INTEGER NOT NULL,
                embedding TEXT,
                faiss_dirty INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memories_session_time ON memories(session_id, timestamp)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memories_faiss_dirty ON memories(faiss_dirty)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memories_turn ON memories(turn_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS kv (
                k TEXT PRIMARY KEY,
                v TEXT NOT NULL
            )
            """
        )
        conn.commit()

        migrated_flag = self._get_kv("migrated") or "0"
        if migrated_flag != "1":
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
            has_messages = cur.fetchone() is not None
            if has_messages:
                cur.execute("SELECT COUNT(1) FROM memories")
                mem_count = int(cur.fetchone()[0])
                if mem_count == 0:
                    cur.execute(
                        "SELECT session_id, role, text, embedding, importance, timestamp FROM messages ORDER BY id ASC"
                    )
                    rows = cur.fetchall()
                    for session_id, role, text, embedding, importance, ts in rows:
                        self._insert_memory_row(
                            cur=cur,
                            uuid_str=str(uuid.uuid4()),
                            turn_id=None,
                            user_id=None,
                            session_id=session_id,
                            role=role,
                            content=text,
                            memory_type="episodic",
                            importance=float(importance),
                            timestamp=int(ts),
                            embedding_json=embedding,
                            faiss_dirty=1,
                        )
                    conn.commit()
            self._set_kv("migrated", "1")

    def _get_kv(self, key: str) -> Optional[str]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT v FROM kv WHERE k=?", (key,))
        row = cur.fetchone()
        return str(row[0]) if row else None

    def _set_kv(self, key: str, value: str) -> None:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO kv(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (key, value))
        conn.commit()

    def _ensure_faiss(self) -> None:
        if self._faiss is not None:
            return
        dim = self._embedding_dim
        if dim is None:
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
            self._embedding_dim = int(len(embedding))
            self._set_kv("embedding_dim", str(self._embedding_dim))
        self._ensure_faiss()

    def _insert_memory_row(
        self,
        cur: sqlite3.Cursor,
        uuid_str: str,
        turn_id: Optional[str],
        user_id: Optional[str],
        session_id: str,
        role: str,
        content: str,
        memory_type: str,
        importance: float,
        timestamp: int,
        embedding_json: Optional[str],
        faiss_dirty: int,
    ) -> int:
        cur.execute(
            """
            INSERT INTO memories(uuid, turn_id, user_id, session_id, role, content, memory_type, importance, timestamp, embedding, faiss_dirty)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid_str,
                turn_id,
                user_id,
                session_id,
                role,
                content,
                memory_type,
                float(importance),
                int(timestamp),
                embedding_json,
                int(faiss_dirty),
            ),
        )
        return int(cur.lastrowid)

    def _thread_state_begin(self, conn: sqlite3.Connection) -> None:
        tid = threading.get_ident()
        if not self._tx_active.get(tid):
            conn.execute("BEGIN")
            self._tx_active[tid] = True
            self._tx_counts[tid] = 0

    def _thread_state_commit_if_needed(self, conn: sqlite3.Connection) -> None:
        tid = threading.get_ident()
        cnt = int(self._tx_counts.get(tid, 0))
        if cnt >= self._batch_size:
            conn.commit()
            self._tx_active[tid] = False
            self._tx_counts[tid] = 0

    def _thread_state_rollback(self, conn: sqlite3.Connection) -> None:
        tid = threading.get_ident()
        if self._tx_active.get(tid):
            conn.rollback()
            self._tx_active[tid] = False
            self._tx_counts[tid] = 0

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
    ) -> int:
        ts = int(timestamp if timestamp is not None else time.time())
        self._ensure_faiss_dim(embedding)
        embedding_json = json.dumps(list(embedding))
        conn = self._get_conn()
        cur = conn.cursor()
        self._thread_state_begin(conn)
        mem_uuid = str(uuid.uuid4())
        mem_id = self._insert_memory_row(
            cur=cur,
            uuid_str=mem_uuid,
            turn_id=turn_id,
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
            memory_type=memory_type,
            importance=float(importance),
            timestamp=ts,
            embedding_json=embedding_json,
            faiss_dirty=1,
        )
        try:
            if self._faiss is not None:
                with self._faiss_lock:
                    self._faiss.add([mem_id], [embedding], normalize=True)
                self._set_faiss_dirty(mem_id, 0)
            self._tx_counts[threading.get_ident()] = self._tx_counts.get(threading.get_ident(), 0) + 1
            self._thread_state_commit_if_needed(conn)
        except Exception:
            self._thread_state_rollback(conn)
            raise
        return int(mem_id)

    def _set_faiss_dirty(self, memory_id: int, dirty: int) -> None:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE memories SET faiss_dirty=? WHERE id=?", (int(dirty), int(memory_id)))
        # Do not force commit here; rely on batch commit

    def rebuild_faiss(self, max_batch: int = 2000) -> int:
        self._ensure_faiss()
        if self._faiss is None:
            return 0
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, embedding FROM memories WHERE faiss_dirty=1 AND embedding IS NOT NULL ORDER BY id ASC LIMIT ?",
            (int(max_batch),),
        )
        rows = cur.fetchall()
        if not rows:
            return 0
        ids: List[int] = []
        vecs: List[List[float]] = []
        for mid, emb_json in rows:
            try:
                emb = json.loads(emb_json)
                if not isinstance(emb, list):
                    continue
                ids.append(int(mid))
                vecs.append([float(x) for x in emb])
            except Exception:
                continue
        if not ids:
            return 0
        with self._faiss_lock:
            self._faiss.add(ids, vecs, normalize=True)
        cur.executemany("UPDATE memories SET faiss_dirty=0 WHERE id=?", [(i,) for i in ids])
        conn.commit()
        return len(ids)

    def insert_message(
        self,
        session_id: str,
        role: str,
        text: str,
        embedding: List[float],
        importance: float,
        timestamp: int,
        MTEW: float = 0.8,
        MTEW_decay: float = 0.1,
    ) -> None:
        self.insert_memory(
            session_id=session_id,
            role=role,
            content=text,
            embedding=embedding,
            importance=importance,
            timestamp=timestamp,
            user_id=None,
            turn_id=None,
            memory_type="episodic",
        )

    def fetch_messages_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memories'")
        has_memories = cur.fetchone() is not None
        if has_memories:
            cur.execute(
                "SELECT role, content, embedding, importance, timestamp, memory_type FROM memories WHERE session_id=? ORDER BY timestamp ASC",
                (session_id,),
            )
            rows = cur.fetchall()
            result: List[Dict[str, Any]] = []
            for role, content, embedding, importance, ts, memory_type in rows:
                result.append(
                    {
                        "role": role,
                        "text": content,
                        "embedding": json.loads(embedding) if embedding else [],
                        "importance": float(importance),
                        "timestamp": int(ts),
                        "memory_type": str(memory_type),
                    }
                )
            return result

        cur.execute(
            "SELECT role, text, embedding, importance, timestamp FROM messages WHERE session_id=? ORDER BY timestamp ASC",
            (session_id,),
        )
        rows = cur.fetchall()
        result2: List[Dict[str, Any]] = []
        for role, text, embedding, importance, ts in rows:
            result2.append(
                {
                    "role": role,
                    "text": text,
                    "embedding": json.loads(embedding),
                    "importance": float(importance),
                    "timestamp": int(ts),
                    "memory_type": "episodic",
                }
            )
        return result2

    def fetch_memories_by_ids(self, ids: Sequence[int]) -> List[Dict[str, Any]]:
        if not ids:
            return []
        placeholders = ",".join(["?"] * len(ids))
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            f"SELECT id, uuid, turn_id, user_id, session_id, role, content, memory_type, importance, timestamp, embedding FROM memories WHERE id IN ({placeholders})",
            tuple(int(x) for x in ids),
        )
        rows = cur.fetchall()
        by_id: Dict[int, Dict[str, Any]] = {}
        for (
            mid,
            uuid_str,
            turn_id,
            user_id,
            session_id,
            role,
            content,
            memory_type,
            importance,
            ts,
            emb_json,
        ) in rows:
            by_id[int(mid)] = {
                "id": int(mid),
                "uuid": str(uuid_str),
                "turn_id": turn_id,
                "user_id": user_id,
                "session_id": str(session_id),
                "role": str(role),
                "text": str(content),
                "memory_type": str(memory_type),
                "importance": float(importance),
                "timestamp": int(ts),
                "embedding": json.loads(emb_json) if emb_json else [],
            }
        return [by_id[int(x)] for x in ids if int(x) in by_id]

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
        ids = [int(x) for x in result.ids.tolist() if int(x) != -1]
        scores = [float(x) for x in result.scores.tolist() if x is not None]
        if not ids:
            return []

        selected_ids: List[int] = []
        selected_scores: List[float] = []
        if filter_strategy == "session_based":
            conn = self._get_conn()
            placeholders = ",".join(["?"] * len(ids))
            cur = conn.cursor()
            cur.execute(
                f"SELECT id FROM memories WHERE session_id=? AND id IN ({placeholders})",
                (session_id, *[int(x) for x in ids]),
            )
            allowed = {int(r[0]) for r in cur.fetchall()}
            for i, mid in enumerate(ids):
                if mid in allowed:
                    selected_ids.append(mid)
                    selected_scores.append(scores[i] if i < len(scores) else 0.0)
                    if len(selected_ids) >= want:
                        break
        else:
            selected_ids = ids[:want]
            selected_scores = scores[:want]

        records = self.fetch_memories_by_ids(selected_ids)
        by_id = {int(r["id"]): r for r in records}
        out: List[Dict[str, Any]] = []
        for i, mid in enumerate(selected_ids):
            r = by_id.get(int(mid))
            if not r:
                continue
            r["similarity"] = max(0.0, float(selected_scores[i] if i < len(selected_scores) else 0.0))
            out.append(r)
        return out
