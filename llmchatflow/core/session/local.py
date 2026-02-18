from typing import Dict, Any, Optional
from .base import ISession

class LocalSession(ISession):
    """Local in-memory session implementation."""

    def __init__(self, session_id: str):
        self._session_id = session_id
        self._context: Dict[str, Any] = {}

    @property
    def session_id(self) -> str:
        return self._session_id

    def load(self) -> None:
        # In a real local implementation, this might load from a JSON file
        pass

    def save(self) -> None:
        # In a real local implementation, this might save to a JSON file
        pass

    def get_context(self) -> Dict[str, Any]:
        return self._context

    def update_context(self, key: str, value: Any) -> None:
        self._context[key] = value
