from __future__ import annotations

from typing import Any

__all__ = [
    "SemanticMemoryEngine",
    "StructuredContextBuilder",
    "OpenAICompatibleClient",
    "MemoryManager",
    "MemoryRetriever",
    "DefaultMemoryPolicy",
    "SQLiteFaissMemoryStore",
    "LocalSession",
    "AppConfig",
]


def __getattr__(name: str) -> Any:
    if name == "SemanticMemoryEngine":
        from .core.workflow import SemanticMemoryEngine

        return SemanticMemoryEngine
    if name == "StructuredContextBuilder":
        from .core.context import StructuredContextBuilder

        return StructuredContextBuilder
    if name == "OpenAICompatibleClient":
        from .core.llm import OpenAICompatibleClient

        return OpenAICompatibleClient
    if name == "MemoryManager":
        from .core.memory import MemoryManager

        return MemoryManager
    if name == "MemoryRetriever":
        from .core.memory import MemoryRetriever

        return MemoryRetriever
    if name == "DefaultMemoryPolicy":
        from .core.memory import DefaultMemoryPolicy

        return DefaultMemoryPolicy
    if name == "SQLiteFaissMemoryStore":
        from .utils import SQLiteFaissMemoryStore

        return SQLiteFaissMemoryStore
    if name == "LocalSession":
        from .core.session import LocalSession

        return LocalSession
    if name == "AppConfig":
        from .config import AppConfig

        return AppConfig
    raise AttributeError(name)
