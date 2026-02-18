from abc import ABC, abstractmethod
from typing import List, Dict


class ContextBuilder(ABC):
    @abstractmethod
    def build_messages(self, session_id: str, user_text: str) -> List[Dict[str, str]]:
        pass
