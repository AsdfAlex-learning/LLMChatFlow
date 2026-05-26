from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class ContextBuilder(ABC):
    """Abstract base class for context builders.

    Given a session and user input, produces a list of chat messages
    ready for LLM consumption (with retrieved memories injected).
    """

    @abstractmethod
    def build_messages(
        self, session_id: str, user_text: str, current_embedding: Optional[List[float]] = None
    ) -> List[Dict[str, str]]:
        pass
