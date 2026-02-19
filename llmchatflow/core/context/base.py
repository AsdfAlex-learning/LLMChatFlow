from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class ContextBuilder(ABC):
    @abstractmethod
    def build_messages(
        self, session_id: str, user_text: str, current_embedding: Optional[List[float]] = None
    ) -> List[Dict[str, str]]:
        pass
