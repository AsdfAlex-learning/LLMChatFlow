from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence


class MemoryStore(ABC):
    """Abstract base class for memory storage backends.

    Defines the interface for inserting, fetching, and searching memory records.
    Concrete implementations (e.g. SQLiteFaissMemoryStore) provide persistence
    and vector search capabilities.
    """

    @abstractmethod
    def insert_memory(
        self,
        session_id: str,
        role: str,
        content: str,
        embedding: List[float],
        importance: float,
        timestamp: Optional[int] = None,
        user_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        memory_type: str = "episodic",
        memory_scope: str = "session",
        decay_rate: float = 0.1,
    ) -> str:
        """Insert a memory record. Returns the UUID of the created record."""
        pass

    @abstractmethod
    def insert_message(
        self,
        session_id: str,
        role: str,
        text: str,
        embedding: List[float],
        importance: float,
        timestamp: int,
        user_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        memory_type: str = "episodic",
        memory_scope: str = "session",
        decay_rate: float = 0.1,
    ) -> None:
        """Convenience method that delegates to insert_memory()."""
        pass

    @abstractmethod
    def fetch_messages_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def fetch_memories_by_uuids(self, uuids: Sequence[str]) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def search_records(
        self,
        session_id: str,
        query_embedding: Sequence[float],
        top_k: int,
        filter_strategy: str = "global",
        oversample: int = 5,
    ) -> List[Dict[str, Any]]:
        pass
