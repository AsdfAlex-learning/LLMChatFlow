from typing import List, Dict
from ...utils.token_counter import count_tokens


def trim_records_to_token_budget(
    records: List[Dict], max_tokens: int, model: str
) -> List[Dict]:
    texts = [r["text"] for r in records]
    total = sum(count_tokens(t, model) for t in texts)
    if total <= max_tokens:
        return records
    recs = list(records)
    recs.sort(key=lambda r: r.get("_score", 0.0))
    while total > max_tokens and recs:
        low = recs.pop(0)
        total -= count_tokens(low["text"], model)
    recs.sort(key=lambda r: r.get("timestamp", 0))
    return recs
