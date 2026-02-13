"""
文件职责：总结触发契约
定义了触发总结生成的“原因”(Reason) 和“策略接口”(Policy)。
解耦了“何时总结”与“如何总结”，支持多种触发源（会话结束、闲置、手动等）。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
import time

# 确保导入了正确的依赖项
from src.core.memory_ingest import MemorySource
from src.core.context_snapshot import ContextSnapshot

class SummaryTriggerReason(Enum):
    """
    请求或考虑生成总结的语义原因。
    """
    SESSION_END = "session_end"          # 明确的会话结束 (例如用户关闭应用)
    USER_IDLE = "user_idle"              # 用户超过阈值时间未活动
    CONTEXT_LIMIT = "context_limit"      # 短期上下文已满
    TOPIC_CHANGE = "topic_change"        # 检测到话题转换 (高级)
    PERIODIC = "periodic"                # 例行检查 (例如每 N 轮)
    MANUAL = "manual"                    # 管理员或调试强制触发

@dataclass
class SummaryHint:
    """
    外部或内部发出的总结建议信号。
    """
    user_id: int                                                # 用户 ID
    source: MemorySource                                        # 信号来源 (例如 MemorySource.LIVE2D)
    reason: SummaryTriggerReason                                # 信号原因
    timestamp: float = field(default_factory=time.time)        # 信号生成时间
    payload: Dict[str, Any] = field(default_factory=dict)      # 可选的上下文数据 (例如 {"idle_seconds": 600})

class ISummaryTriggerPolicy(ABC):
    """
    决定是否应生成长期记忆总结的策略接口。
    
    此接口将“决策逻辑”(何时总结) 与“执行逻辑”(如何总结) 和“触发源”(谁要求的) 解耦。
    """

    @abstractmethod
    def should_trigger(self, snapshot: ContextSnapshot, hint: Optional[SummaryHint] = None) -> bool:
        """
        评估当前状态和可选的提示，以决定是否需要进行总结。
        
        逻辑示例:
            - 如果 hint.reason == SESSION_END: 返回 True
            - 如果 snapshot.state.interaction_depth > 20: 返回 True
            - 如果 hint.reason == USER_IDLE 且 snapshot.state.interaction_depth < 3: 返回 False (太短，不总结)
            
        Args:
            snapshot (ContextSnapshot): 用户上下文的当前只读快照。
                                        用于检查交互深度、情绪、最近消息等。
            hint (Optional[SummaryHint]): 可选的外部建议。
                                          如果为 None，则暗示是例行的内部检查。
        
        Returns:
            bool: 如果 SummaryAgent 应该继续生成总结，则返回 True。
        """
        # TODO: 实现具体的触发策略类。
        pass
