"""
文件职责：上下文快照定义
定义了只读的 ContextSnapshot 数据结构，用于跨模块（特别是外部模块如 Live2D）
同步当前会话的状态，而不暴露 Core 的内部实现。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import uuid
import time
import json

@dataclass
class SnapshotMeta:
    """
    上下文快照的元数据
    """
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))  # 快照的唯一标识符 (UUID v4)
    timestamp: float = field(default_factory=time.time)                  # 快照生成时的 Unix 时间戳
    version: str = "1.0"                                                 # 快照结构的版本号

@dataclass
class SessionInfo:
    """
    当前用户会话的信息
    """
    user_id: int                                # 用户的唯一标识符
    active_session_id: str                     # 当前活跃会话的唯一标识符
    is_private_mode: bool                      # 是否处于隐私模式（仅限 Owner）

@dataclass
class InteractionState:
    """
    当前的交互状态
    """
    current_mood: str = ""                     # AI 当前的情感状态（例如 "happy", "curious"）
    interaction_depth: int = 0                 # 当前会话的轮次深度
    last_active_component: str = ""            # 触发最后一次更新的组件（例如 "telegram", "live2d"）

@dataclass
class ShortTermMessage:
    """
    短期上下文窗口中的单条消息。
    """
    role: str                                   # 消息发送者的角色 ("user", "assistant", "system")
    content: str                                # 消息的文本内容
    timestamp: float                            # 消息的时间戳
    source: Optional[str] = None               # 消息来源平台 (例如 "live2d", "telegram")
    mood_tag: Optional[str] = None             # 与此消息关联的情感标签（仅用于 assistant 消息）

@dataclass
class ContextSnapshot:
    """
    当前上下文状态的只读快照。
    
    此对象代表对话在某一时刻的完整视图，适用于外部客户端（如 Live2D）
    用于渲染 UI 或决定动画逻辑。
    它是不可变的，并且不暴露 Core 的内部实现细节。
    """
    meta: SnapshotMeta                              # 快照的元数据
    session: SessionInfo                            # 当前会话的信息
    state: InteractionState                         # 当前的交互状态
    short_term_context: List[ShortTermMessage]     # 短期上下文窗口中的消息列表

    def to_json(self) -> str:
        """
        将快照序列化为 JSON 字符串。
        """
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextSnapshot':
        """
        将字典反序列化为 ContextSnapshot 对象。
        """
        meta = SnapshotMeta(**data.get('meta', {}))
        session = SessionInfo(**data.get('session', {}))
        state = InteractionState(**data.get('state', {}))
        
        context_data = data.get('short_term_context', [])
        short_term_context = [ShortTermMessage(**msg) for msg in context_data]
        
        return cls(
            meta=meta,
            session=session,
            state=state,
            short_term_context=short_term_context
        )

class SnapshotService:
    """
    负责生成 ContextSnapshot 的服务
    
    此服务驻留在 Core 内部，可以访问内部的 ContextManager
    """
    
    def generate_snapshot(self, user_id: int) -> ContextSnapshot:
        """
        为指定用户生成新的快照。
        
        生命周期:
            - 应在每次 Core 交互循环结束后调用 (User Input -> LLM -> Update)。
            - 应反映最新的已提交状态。
        
        Args:
            user_id (int): 要生成快照的用户 ID。
            
        Returns:
            ContextSnapshot: 新的快照对象。
        """
        # TODO: 实现快照生成逻辑。需要访问 ChatService/ContextManager 来获取真实数据。
        raise NotImplementedError("此方法应由具体的 Core 服务实现。")
