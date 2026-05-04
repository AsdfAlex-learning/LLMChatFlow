from abc import ABC, abstractmethod
from typing import Any, Dict, List


class MemoryPolicy(ABC):
    """Abstract base class for memory scoring and selection policies.

    A MemoryPolicy encapsulates the decision logic for how memories are
    scored and selected during retrieval. The default policy covers 80%
    of common scenarios; custom policies can override for specialized needs.
    """

    @abstractmethod
    def score(
        self,
        memory: Dict[str, Any],
        query_vector: List[float],
        **kwargs,
    ) -> float:
        """Score a single memory record against the query.

        Args:
            memory: A memory dict with keys: id, text, memory_type, importance,
                    decay_rate, timestamp, similarity, etc.
            query_vector: The embedding of the user query.

        Returns:
            A float score representing the memory's relevance.
        """
        ...

    @abstractmethod
    def select(
        self,
        memories: List[Dict[str, Any]],
        query_vector: List[float],
        config: Any = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Select and rank memories from a candidate list.

        Args:
            memories: Candidate memory dicts (already retrieved from store).
            query_vector: The embedding of the user query.
            config: Optional AppConfig for parameter-driven behavior.

        Returns:
            Ranked list of selected memory dicts, each with '_score' field set.
        """
        ...
