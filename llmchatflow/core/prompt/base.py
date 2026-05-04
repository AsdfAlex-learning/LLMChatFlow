from abc import ABC, abstractmethod
from typing import Dict, List


class PromptTemplate(ABC):
    @abstractmethod
    def assemble(self, blocks: Dict[str, str], user_text: str) -> List[Dict[str, str]]:
        """Assemble prompt messages from structured context blocks and user text.

        blocks keys: "system_prompt", "history_summary", "retrieved_memories"
        Each block value is a pre-formatted string (may be empty).
        user_text is the current user input.
        """
        pass
