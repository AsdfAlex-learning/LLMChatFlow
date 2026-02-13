"""
文件职责：记忆仓储层 (Repository)
负责底层数据存储与检索，直接操作 SQLite 数据库和 CSV 备份。
不包含任何业务规则（如过期、重要性筛选），只提供纯粹的 CRUD 接口。
"""

import sqlite3
import csv
import os
import threading
from typing import List, Tuple, Optional, Any
from src.core.logger import get_logger

logger = get_logger("MemoryRepository")

class MemoryRepository:
    def __init__(self, user_id: int, data_dir: str):
        self.user_id = user_id
        self.db_path = os.path.join(data_dir, f"user_{user_id}.db")
        self.csv_path = os.path.join(data_dir, f"user_{user_id}_backup.csv")
        self.lock = threading.Lock()
        self._init_database()

    def _init_database(self):
        """初始化数据库表结构"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS memories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event TEXT NOT NULL,
                        keywords TEXT NOT NULL,
                        importance INTEGER NOT NULL,
                        create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expiry_days INTEGER NOT NULL,
                        last_mentioned TIMESTAMP
                    )
                ''')
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"[REPO] INIT_FAIL | user_id: {self.user_id} | error: {e}")
                raise

    def add_memory(self, event: str, keywords: str, importance: int, expiry_days: int) -> int:
        """
        添加单条记忆。
        Returns:
            int: 新插入记录的 ID
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO memories (event, keywords, importance, expiry_days)
                VALUES (?, ?, ?, ?)
            ''', (event, keywords, importance, expiry_days))
            memory_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return memory_id

    def get_all_memories(self) -> List[Tuple]:
        """获取所有记忆（未过滤）"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM memories")
            rows = cursor.fetchall()
            conn.close()
            return rows

    def get_memories_by_sql(self, where_clause: str, params: tuple = ()) -> List[Tuple]:
        """
        通过自定义 SQL 条件查询记忆。
        注意：仅供 Policy 层构建复杂查询使用。
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            query = f"SELECT * FROM memories WHERE {where_clause}"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            return rows

    def update_memory_importance(self, memory_id: int, new_importance: float):
        """更新记忆重要性"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE memories SET importance = ? WHERE id = ?", (new_importance, memory_id))
            conn.commit()
            conn.close()

    def update_last_mentioned(self, memory_id: int):
        """更新记忆最后提及时间为当前时间"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE memories SET last_mentioned = CURRENT_TIMESTAMP WHERE id = ?",
                (memory_id,)
            )
            conn.commit()
            conn.close()

    def delete_memory(self, memory_id: int):
        """删除指定 ID 的记忆"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            conn.close()

    def delete_memories_batch(self, memory_ids: List[int]):
        """批量删除记忆"""
        if not memory_ids:
            return
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            placeholders = ','.join('?' for _ in memory_ids)
            cursor.execute(f"DELETE FROM memories WHERE id IN ({placeholders})", memory_ids)
            conn.commit()
            conn.close()

    def backup_to_csv(self):
        """将当前数据库全量备份到 CSV"""
        try:
            rows = self.get_all_memories()
            with self.lock:
                with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['id', 'event', 'keywords', 'importance', 'create_time', 'expiry_days', 'last_mentioned'])
                    writer.writerows(rows)
        except Exception as e:
            logger.error(f"[REPO] CSV_BACKUP_FAIL | user_id: {self.user_id} | error: {e}")
