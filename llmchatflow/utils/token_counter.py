import tiktoken
from typing import Optional


def count_tokens(text: str, model: Optional[str] = None) -> int:
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return len(text.split())
