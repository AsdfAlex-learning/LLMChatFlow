"""
文件职责：记忆注入接口
定义了结构化的记忆数据载体 (MemoryPayload) 和记忆管理接口 (MemoryManagerInterface)。
确保所有进入长期记忆的数据（无论来源）都遵循统一的格式和追溯标准。
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import List
from abc import ABC, abstractmethod

class MemorySource(Enum):
    """
    有效记忆来源的枚举。
    
    确保每个记忆条目的来源都是可追溯的。
    """
    TELEGRAM = "telegram"
    LIVE2D = "live2d"
    SYSTEM_EVENT = "system"

@dataclass
class MemoryPayload:
    """
    用于注入新的长期记忆总结的数据载体。
    
    此结构确保只有经过总结的结构化数据进入记忆系统，而不是原始聊天记录。
    """
    summary_text: str                                              # LLM 生成的纯文本总结
    keywords: List[str]                                            # 从交互中提取的关键标签
    importance_score: float                                        # 0.0 到 1.0 的权重，指示记忆保留的优先级
    related_context_ids: List[str]                                 # 生成此总结的原始消息/交互的 ID (用于溯源)
    source_platform: MemorySource                                  # 交互发生的来源平台
    timestamp: datetime                                            # 记忆形成的时间 (通常是现在，或会话结束时间)

class MemoryManagerInterface(ABC):
    """
    记忆管理器的抽象接口。
    
    定义了与长期记忆存储交互的契约。
    此接口确保外部模块（如 Live2D）或内部代理遵守 'Ingest' 协议，
    而不是直接写入数据库。
    """

    @abstractmethod
    def ingest_summary(self, user_id: int, payload: MemoryPayload) -> bool:
        """
        注入长期记忆的标准入口。
        
        此方法充当记忆数据库的防火墙。它负责：
        1. 校验 payload 合法性 (例如：文本非空，分数在范围内)。
        2. 执行去重检查 (例如：向量相似度对比)。
        3. 将数据持久化到向量存储和 SQL 数据库。
        4. 触发任何必要的清理或衰减任务。
        
        约束:
            - 仅限 Core 内部服务调用 (SummaryAgent, BackgroundWorker)。
            - 外部客户端 (Live2D) 绝对禁止直接调用此方法。
        
        Args:
            user_id (int): 拥有此记忆的用户 ID。
            payload (MemoryPayload): 要注入的结构化记忆数据。
            
        Returns:
            bool: 如果注入成功则返回 True，否则返回 False。
        """
        # TODO: 实现具体的记忆注入逻辑 (SQLite/VectorDB)。
        pass
