from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseRenderer(ABC):
    """
    渲染器基类
    负责将抽象的表达内容（文本、动作）转换为特定平台的格式
    """
    @abstractmethod
    def render(self, content: Any) -> Any:
        pass

class BaseClient(ABC):
    """
    客户端基类 (Input/Output Adapter)
    抽象了具体的通信渠道（Telegram, Discord, Web等）
    
    它是一个单纯的“播放器”容器：
    1. 不做业务逻辑
    2. 不判断“该不该动”
    3. 只负责执行指令
    """
    
    @abstractmethod
    async def send_text(self, target_id: str, text: str):
        """发送纯文本"""
        pass
        
    @abstractmethod
    async def play_action(self, target_id: str, action_name: str):
        """
        播放/执行动作 
        (e.g. Live2D 动作, Sticker, 状态指示)
        """
        pass
        
    @abstractmethod
    async def play_voice(self, target_id: str, audio_data: bytes):
        """播放语音"""
        pass
