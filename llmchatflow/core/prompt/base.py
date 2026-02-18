from abc import ABC, abstractmethod
from typing import List, Dict


class PromptTemplate(ABC):
    @abstractmethod
    def assemble(self, history_text: str, user_text: str) -> List[Dict[str, str]]:
        pass
