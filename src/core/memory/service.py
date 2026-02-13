"""
文件职责：记忆服务层 (Service)
核心业务逻辑入口，组装 Repository 和 Policy。
对外提供记忆的增删改查、自动维护和检索功能。
"""

import os
from typing import List, Tuple, Optional
from src.core.logger import get_logger
from src.core.memory.repository import MemoryRepository
from src.core.memory.policy import MemoryPolicy

logger = get_logger("MemoryService")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
USER_MEMORIES_DIR = os.path.join(PROJECT_ROOT, "user_memories")
os.makedirs(USER_MEMORIES_DIR, exist_ok=True)

class MemoryService:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.repo = MemoryRepository(user_id, USER_MEMORIES_DIR)
        self.policy = MemoryPolicy()

    def add_memories(self, new_memories: List[Tuple[str, str, int, int]]):
        """
        批量添加新记忆。
        格式: [(event, keywords, importance, expiry_days), ...]
        包含去重和维护逻辑。
        """
        if not new_memories:
            return

        # 1. 执行一次维护（衰减旧记忆）
        self._perform_maintenance()

        # 2. 处理新记忆
        for mem in new_memories:
            event, keywords, importance, expiry_days = mem
            
            try:
                # 尝试查找包含相同关键词或类似文本的记忆
                where_clause, params = self.policy.get_duplicate_candidates_sql(event)
                candidates = self.repo.get_memories_by_sql(where_clause, params)
                
                is_duplicate = False
                for existing in candidates:
                    # existing: id, event, keywords, imp, create, expiry, last
                    e_id, e_event, _, e_imp, _, _, _ = existing
                    
                    if self.policy.is_duplicate(event, e_event):
                        if self.policy.should_replace_duplicate(importance, e_imp):
                            # 新记忆更重要，替换旧的（先删旧）
                            self.repo.delete_memory(e_id)
                            logger.info(f"[MEMORY] REPLACE | user_id: {self.user_id} | old_id: {e_id} | new_event: {event}")
                        else:
                            # 旧记忆更重要，忽略新的
                            is_duplicate = True
                            logger.info(f"[MEMORY] IGNORE_DUPLICATE | user_id: {self.user_id} | event: {event}")
                        break
                
                if not is_duplicate:
                    self.repo.add_memory(event, keywords, importance, expiry_days)
                    logger.info(f"[MEMORY] ADD | user_id: {self.user_id} | event: {event}")

            except Exception as e:
                logger.error(f"[MEMORY] ADD_FAIL | user_id: {self.user_id} | error: {e}")

        # 3. 再次清理低重要性记忆
        self._cleanup_low_importance()
        
        # 4. 备份
        self.repo.backup_to_csv()

    def get_relevant_memories(self) -> List[Tuple]:
        """
        获取当前有效的、高重要性的记忆用于构建 Prompt。
        """
        where_clause, params = self.policy.get_valid_memories_sql()
        return self.repo.get_memories_by_sql(where_clause, params)

    def search_memories(self, query_keywords: List[str], limit: int = 2) -> List[Tuple]:
        """
        根据关键词搜索相关记忆。
        """
        # 获取所有较高权重的记忆进行匹配
        where_clause, params = self.policy.get_search_candidates_sql()
        candidates = self.repo.get_memories_by_sql(where_clause, params)
        
        matched = []
        for mem in candidates:
            # mem[2] is keywords string
            if self.policy.match_keywords(mem[2], query_keywords):
                matched.append(mem)
                if len(matched) >= limit:
                    break
        return matched

    def update_last_mentioned(self, memory_id: int):
        """更新记忆的活跃时间"""
        self.repo.update_last_mentioned(memory_id)

    def _perform_maintenance(self):
        """执行维护：衰减重要性"""
        all_memories = self.repo.get_all_memories()
        for mem in all_memories:
            mem_id, _, _, imp, _, _, last_mentioned = mem
            new_imp = self.policy.calculate_decay(imp, last_mentioned)
            
            if self.policy.should_persist_decay(imp, new_imp):
                self.repo.update_memory_importance(mem_id, new_imp)

    def _cleanup_low_importance(self):
        """清理重要性过低或过期的记忆"""
        to_delete = []
        all_memories = self.repo.get_all_memories()
        
        for mem in all_memories:
            # mem结构: id, event, keywords, importance, create_time, expiry_days, last_mentioned
            mem_id, _, _, imp, create_time, expiry_days, last_mentioned = mem
            
            if self.policy.should_delete_memory(imp, create_time, expiry_days, last_mentioned):
                to_delete.append(mem_id)

        if to_delete:
            self.repo.delete_memories_batch(to_delete)
            logger.info(f"[MEMORY] CLEANUP | user_id: {self.user_id} | count: {len(to_delete)}")
