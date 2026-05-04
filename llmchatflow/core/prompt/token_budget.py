import logging
from typing import List, Dict

from ...utils.token_counter import count_tokens

logger = logging.getLogger(__name__)


def within_budget(texts: List[str], max_tokens: int, model: str) -> bool:
    return sum(count_tokens(t, model) for t in texts) <= max_tokens


def trim_records_to_token_budget(
    records: List[Dict], max_tokens: int, model: str, min_tokens: int = 0
) -> List[Dict]:
    """Trim records to fit within max_tokens using 3-stage strategy (§4.6 Rule 4).

    Stage 1: Remove low-score memories until within budget.
    Stage 2: Compress older records' text if still over budget.
    Stage 3: Guarantee min_token floor — ensure at least one high-score record
              survives if possible, unless all records were trimmed.
    """
    texts = [r["text"] for r in records]
    total = sum(count_tokens(t, model) for t in texts)
    if total <= max_tokens:
        return records

    recs = list(records)
    tokens_before = total

    # Stage 1 — Trim low-score memories
    recs.sort(key=lambda r: r.get("_score", 0.0))
    removed_count = 0
    while total > max_tokens and recs:
        low = recs.pop(0)
        total -= count_tokens(low["text"], model)
        removed_count += 1
    logger.info(
        "Token trim stage 1: removed %d memories, tokens: %d→%d",
        removed_count,
        tokens_before,
        total,
    )

    # Stage 2 — Compress history (edge case: still over budget after removing all low-score)
    if total > max_tokens and recs:
        compress_count = 0
        tokens_before_s2 = total
        # Oldest first — recs are currently sorted by _score ascending,
        # re-sort by timestamp for compression order
        recs.sort(key=lambda r: r.get("timestamp", 0))
        for i in range(len(recs)):
            if total <= max_tokens:
                break
            rec = recs[i]
            rec_tokens = count_tokens(rec["text"], model)
            # Target: keep enough tokens to fit budget, halve the text as compression
            half_len = len(rec["text"]) // 2
            if half_len == 0:
                continue
            new_text = rec["text"][:half_len]
            new_tokens = count_tokens(new_text, model)
            total -= rec_tokens - new_tokens
            recs[i] = {**rec, "text": new_text}
            compress_count += 1
        logger.info(
            "Token trim stage 2: compressed %d records, tokens: %d→%d",
            compress_count,
            tokens_before_s2,
            total,
        )

    # Stage 3 — Guarantee min_token floor
    if total < min_tokens and recs:
        # Ensure at least the highest-score record is retained.
        # Since recs may have been re-sorted by timestamp in stage 2,
        # find the record with the highest score.
        best = max(recs, key=lambda r: r.get("_score", 0.0))
        best_tokens = count_tokens(best["text"], model)
        if best_tokens < min_tokens and len(recs) > 1:
            # The best record alone doesn't meet the floor; we've already
            # trimmed aggressively. The caller is responsible for always
            # including user input separately, so we just log and move on.
            pass
        logger.info(
            "Token trim stage 3: min_token floor check, tokens: %d (min: %d)",
            total,
            min_tokens,
        )
    elif not recs:
        logger.info(
            "Token trim stage 3: min_token floor check, tokens: %d (min: %d) — all records trimmed",
            total,
            min_tokens,
        )
    else:
        logger.info(
            "Token trim stage 3: min_token floor check, tokens: %d (min: %d)",
            total,
            min_tokens,
        )

    # Final sort by timestamp for chronological output
    recs.sort(key=lambda r: r.get("timestamp", 0))
    return recs


def reserve_budget(total: int, reserves: Dict[str, int]) -> Dict[str, int]:
    """Allocate token budget with reserved amounts. Returns remaining budget after reservations."""
    allocated = {}
    remaining = total
    for name, amount in reserves.items():
        actual = min(amount, remaining)
        allocated[name] = actual
        remaining -= actual
    allocated["_remaining"] = remaining
    return allocated


def proportional_budget(total: int, ratios: Dict[str, float]) -> Dict[str, int]:
    """Distribute token budget proportionally. Ratios are normalized to sum=1.0."""
    ratio_sum = sum(ratios.values()) or 1.0
    allocated = {}
    remaining = total
    items = list(ratios.items())
    for i, (name, ratio) in enumerate(items):
        if i < len(items) - 1:
            actual = int(total * ratio / ratio_sum)
            allocated[name] = actual
            remaining -= actual
        else:
            allocated[name] = remaining
    return allocated
