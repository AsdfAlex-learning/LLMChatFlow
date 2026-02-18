from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class ISession(ABC):
    """Abstract base class for Session Management."""

    @property
    @abstractmethod
    def session_id(self) -> str:
        pass

    @abstractmethod
    def load(self) -> None:
        pass

    @abstractmethod
    def save(self) -> None:
        pass

    @abstractmethod
    def get_context(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def update_context(self, key: str, value: Any) -> None:
        pass
