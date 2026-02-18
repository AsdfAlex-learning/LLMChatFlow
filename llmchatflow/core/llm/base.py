from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Union


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Synchronous chat completion."""
        pass

    @abstractmethod
    async def achat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Asynchronous chat completion."""
        pass
