from typing import List, Dict
from ...utils.token_counter import count_tokens


def within_budget(texts: List[str], max_tokens: int, model: str) -> bool:
    return sum(count_tokens(t, model) for t in texts) <= max_tokens
