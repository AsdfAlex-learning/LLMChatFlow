from abc import ABC, abstractmethod
from typing import List, Dict, Any

class MemoryRetriever(ABC):
    """Abstract base class for Memory Retrieval."""

    @abstractmethod
    def add(self, role: str, content: str) -> None:
        pass

    @abstractmethod
    def get_messages(self) -> List[Dict[str, str]]:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass
