"""
文件职责：记忆策略层 (Policy)
定义记忆的生命周期规则、检索匹配逻辑和维护策略。
理想状态下是纯函数式设计，不直接持有数据或状态。
MemoryPolicy = 业务规则 + 查询条件生成
"""

from datetime import datetime, timedelta
from typing import List, Tuple, Any

class MemoryPolicy:
    # 核心配置常量
    MIN_RETRIEVAL_IMPORTANCE = 30    # 提取记忆的最低重要性阈值
    MIN_STORAGE_IMPORTANCE = 10      # 存储记忆的最低重要性阈值 (低于此值将被清理)
    DECAY_RATE_ACTIVE = 0.98         # 活跃记忆的衰减率 (7天内被提及)
    DECAY_RATE_INACTIVE = 0.95       # 非活跃记忆的衰减率
    PERMANENT_EXPIRY_DAYS = 365      # 永久记忆的 expiry_days 标记
    ACTIVE_WINDOW_DAYS = 7           # 判定为活跃的时间窗口

    @staticmethod
    def is_expired(create_time_str: str, expiry_days: int) -> bool:
        """判断记忆是否过期"""
        if expiry_days == MemoryPolicy.PERMANENT_EXPIRY_DAYS:
            return False
        
        create_time = datetime.fromisoformat(create_time_str) if isinstance(create_time_str, str) else create_time_str
        # 处理 sqlite 可能返回的 datetime 字符串格式差异
        if isinstance(create_time, str):
             # 简单处理，假设格式标准
             pass
             
        deadline = create_time + timedelta(days=expiry_days)
        return datetime.now() > deadline

    @staticmethod
    def calculate_decay(current_importance: float, last_mentioned_str: str = None) -> float:
        """计算衰减后的新重要性"""
        if last_mentioned_str:
            try:
                last_mentioned = datetime.fromisoformat(last_mentioned_str)
                if last_mentioned >= datetime.now() - timedelta(days=MemoryPolicy.ACTIVE_WINDOW_DAYS):
                    return current_importance * MemoryPolicy.DECAY_RATE_ACTIVE
            except ValueError:
                pass
        
        return current_importance * MemoryPolicy.DECAY_RATE_INACTIVE

    @staticmethod
    def is_duplicate(new_event: str, existing_event: str) -> bool:
        """
        判断是否为重复记忆。
        目前使用简单的包含关系或关键词匹配，未来可升级为语义相似度。
        """
        # 简单策略：如果事件描述高度重合 (这里简化为子串检查，实际可能需要更复杂的 NLP)
        # 假设 event 格式为 "YYYY-MM-DD 具体事件"
        # 提取具体事件部分
        try:
            new_content = new_event.split(' ', 1)[1]
            existing_content = existing_event.split(' ', 1)[1]
            return new_content in existing_content or existing_content in new_content
        except IndexError:
            return new_event == existing_event

    @staticmethod
    def match_keywords(memory_keywords_str: str, query_keywords: List[str]) -> bool:
        """判断记忆关键词是否匹配查询关键词"""
        mem_kws = [k.strip() for k in memory_keywords_str.split(',')]
        return any(q_kw in mem_kws for q_kw in query_keywords)

    @staticmethod
    def should_replace_duplicate(new_importance: int, old_importance: int) -> bool:
        """
        决策：当发现重复记忆时，是否应该用新记忆替换旧记忆。
        """
        return new_importance > old_importance

    @staticmethod
    def should_persist_decay(old_importance: float, new_importance: float) -> bool:
        """
        决策：重要性衰减是否显著到需要更新数据库。
        减少微小变化导致的 IO 写操作。
        """
        return abs(new_importance - old_importance) > 0.1

    @staticmethod
    def should_delete_memory(importance: float, create_time: Any, expiry_days: int, last_mentioned: Any) -> bool:
        """
        决策：该记忆是否应该被物理删除。
        条件：
        1. 重要性低于阈值
        2. OR (已过期 AND 长期未活跃)
        """
        # 1. 重要性检查
        if importance < MemoryPolicy.MIN_STORAGE_IMPORTANCE:
            return True

        # 2. 过期检查
        is_expired = False
        if expiry_days != MemoryPolicy.PERMANENT_EXPIRY_DAYS:
            # 统一转为 datetime 对象
            ct = create_time
            if isinstance(ct, str):
                ct = datetime.fromisoformat(ct)
            
            deadline = ct + timedelta(days=expiry_days)
            if datetime.now() > deadline:
                is_expired = True

        if not is_expired:
            return False

        # 3. 活跃度保护 (即使过期，如果最近 7 天活跃过，也不删)
        if last_mentioned:
            lm = last_mentioned
            if isinstance(lm, str):
                lm = datetime.fromisoformat(lm)
            
            if lm >= datetime.now() - timedelta(days=MemoryPolicy.ACTIVE_WINDOW_DAYS):
                return False # 最近活跃，保留

        return True # 过期且不活跃，删除

    @staticmethod
    def get_valid_memories_sql() -> Tuple[str, tuple]:
        """
        返回用于获取有效记忆的 SQL WHERE 子句和参数。
        有效定义：重要性 >= 30 且 (永久 或 未过期)
        """
        sql = """
            importance >= ? 
            AND (expiry_days = ? OR create_time >= datetime('now', '-' || expiry_days || ' days'))
        """
        return sql, (MemoryPolicy.MIN_RETRIEVAL_IMPORTANCE, MemoryPolicy.PERMANENT_EXPIRY_DAYS)

    @staticmethod
    def get_duplicate_candidates_sql(event: str) -> Tuple[str, tuple]:
        """
        返回用于查找潜在重复记忆的 SQL WHERE 子句和参数。
        策略：提取事件内容（去除时间前缀），进行模糊匹配。
        """
        # 提取事件内容部分用于模糊匹配
        event_content = event.split(' ', 1)[1] if ' ' in event else event
        return "event LIKE ?", (f"%{event_content}%",)

    @staticmethod
    def get_search_candidates_sql() -> Tuple[str, tuple]:
        """
        返回用于搜索候选记忆的 SQL WHERE 子句和参数。
        策略：仅搜索重要性较高的记忆。
        """
        return "importance >= ?", (MemoryPolicy.MIN_SEARCH_IMPORTANCE,)
