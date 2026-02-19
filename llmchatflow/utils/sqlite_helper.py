import sqlite3
import json
import os
from typing import List, Dict, Any, Tuple
from llmchatflow.core.memory.storage import MemoryStore


class SQLiteMemoryStore(MemoryStore):
    def __init__(self, db_path: str = "memory.db"):
        self.db_path = db_path
        os.makedirs(
            os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True
        )
        self._ensure_tables()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _ensure_tables(self):
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT CHECK(role IN ('user','assistant')) NOT NULL,
                    text TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    importance REAL NOT NULL,
                    timestamp INTEGER NOT NULL,
                    MTEW REAL DEFAULT 0.8,
                    MTEW_decay REAL DEFAULT 0.1
                )
                """
            )
            # Migration for existing tables
            try:
                cur.execute("ALTER TABLE messages ADD COLUMN MTEW REAL DEFAULT 0.8")
                cur.execute(
                    "ALTER TABLE messages ADD COLUMN MTEW_decay REAL DEFAULT 0.1"
                )
            except sqlite3.OperationalError:
                pass  # Columns likely exist

            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_session_time ON messages(session_id, timestamp)"
            )
            conn.commit()
        finally:
            conn.close()

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
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO messages(session_id, role, text, embedding, importance, timestamp, MTEW, MTEW_decay) VALUES (?,?,?,?,?,?,?,?)",
                (
                    session_id,
                    role,
                    text,
                    json.dumps(embedding),
                    importance,
                    timestamp,
                    MTEW,
                    MTEW_decay,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def fetch_messages_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT role, text, embedding, importance, timestamp FROM messages WHERE session_id=? ORDER BY timestamp ASC",
                (session_id,),
            )
            rows = cur.fetchall()
            result = []
            for role, text, embedding, importance, ts in rows:
                result.append(
                    {
                        "role": role,
                        "text": text,
                        "embedding": json.loads(embedding),
                        "importance": float(importance),
                        "timestamp": int(ts),
                    }
                )
            return result
        finally:
            conn.close()
