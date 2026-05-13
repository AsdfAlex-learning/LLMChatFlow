from .base import MemoryRetriever
from .policy import MemoryPolicy, DefaultMemoryPolicy

__all__ = ["MemoryRetriever", "MemoryPolicy", "DefaultMemoryPolicy", "MemoryManager"]


def __getattr__(name: str):
    if name == "MemoryManager":
        from .manager import MemoryManager

        return MemoryManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
