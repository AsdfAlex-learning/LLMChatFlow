from .retriever import MemoryRetriever
from .policy import MemoryPolicy, DefaultMemoryPolicy
from .storage import MemoryStore

__all__ = ["MemoryRetriever", "MemoryPolicy", "DefaultMemoryPolicy", "MemoryStore", "MemoryManager"]


def __getattr__(name: str):
    if name == "MemoryManager":
        from .manager import MemoryManager

        return MemoryManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
