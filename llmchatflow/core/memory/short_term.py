from typing import List, Dict, Any
from .base import MemoryRetriever

class ShortTermMemory(MemoryRetriever):
    """Sliding window short-term memory."""

    def __init__(self, limit: int = 10):
        self.limit = limit
        self.messages: List[Dict[str, str]] = []

    def add(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.limit:
            self.messages.pop(0)

    def get_messages(self) -> List[Dict[str, str]]:
        return self.messages

    def clear(self) -> None:
        self.messages = []
