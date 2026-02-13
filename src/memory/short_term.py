from typing import List, Dict
from dataclasses import dataclass, field
import time

@dataclass
class Message:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)

class ShortTermMemory:
    """
    短期记忆 (Working Memory)
    维护当前对话上下文窗口
    """
    
    def __init__(self, limit: int = 20):
        self.messages: List[Message] = []
        self.limit = limit

    def add_message(self, role: str, content: str):
        self.messages.append(Message(role=role, content=content))
        if len(self.messages) > self.limit:
            self.messages.pop(0)

    def get_context(self) -> List[Dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in self.messages]

    def clear(self):
        self.messages = []
