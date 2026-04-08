from __future__ import annotations

from typing import Any

__all__ = ["SemanticMemoryEngine", "StructuredContextBuilder", "OpenAICompatibleClient"]


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
    raise AttributeError(name)
