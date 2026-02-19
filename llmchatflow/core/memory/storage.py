from abc import ABC, abstractmethod
from typing import List, Dict, Any


class MemoryStore(ABC):
    @abstractmethod
    def insert_message(
        self,
        session_id: str,
        role: str,
        text: str,
        embedding: List[float],
        importance: float,
        timestamp: int,
        MTEW: float,          # Memory Time-Efficiency Weight
        MTEW_decay: float,    # Memory Time-Efficiency Decay Rate
    ) -> None:
        pass

    @abstractmethod
    def fetch_messages_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        pass
