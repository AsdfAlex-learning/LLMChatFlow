from typing import Dict, Any, Optional
from .base import ISession

class LocalSession(ISession):
    """Local in-memory session implementation.

    Data is kept in memory only and not persisted to disk.
    load()/save() are no-ops; use a persistent session implementation
    for durability across process restarts.
    """

    def __init__(self, session_id: str):
        self._session_id = session_id
        self._context: Dict[str, Any] = {}

    @property
    def session_id(self) -> str:
        return self._session_id

    def load(self) -> None:
        """No-op for in-memory session. Data is not persisted."""

    def save(self) -> None:
        """No-op for in-memory session. Data is not persisted."""

    def get_context(self) -> Dict[str, Any]:
        return self._context

    def update_context(self, key: str, value: Any) -> None:
        self._context[key] = value
