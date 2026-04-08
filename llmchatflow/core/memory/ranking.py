import math
from typing import List, Dict, Tuple
import time

# Importance constants
IMPORTANCE_HABIT = 1.0  # Represents a user habit or long-term preference
IMPORTANCE_USER_MSG = 0.9
IMPORTANCE_AI_MSG = 0.7


def temporal_score(ts: int, now_ts: int, lam: float) -> float:
    delta_days = max(0.0, (now_ts - ts) / 86400.0)
    return math.exp(-lam * delta_days)


def recency_scores(sorted_by_time_records: List[Dict]) -> List[float]:
    n = len(sorted_by_time_records)
    scores = [0.1] * n
    for i in range(n):
        rank = n - i
        if rank == 1:
            scores[i] = 1.0
        elif rank == 2:
            scores[i] = 0.8
        elif rank == 3:
            scores[i] = 0.6
        elif rank == 4:
            scores[i] = 0.4
        elif rank == 5:
            scores[i] = 0.2
        else:
            scores[i] = 0.1
    return scores


def compute_final_scores(
    records: List[Dict],
    cos_sims: List[float],
    lam: float = 0.1,
    alpha: float = 0.5,
    beta: float = 0.2,
    gamma: float = 0.15,
    delta: float = 0.15,
) -> List[Tuple[float, Dict]]:
    now_ts = int(time.time())
    rec_scores = recency_scores(records)
    out = []
    for i, r in enumerate(records):
        imp = float(r.get("importance", 0.0))
        ts = int(r.get("timestamp", now_ts))
        t_score = temporal_score(ts, now_ts, lam)
        c = cos_sims[i] if i < len(cos_sims) else 0.0
        rc = rec_scores[i] if i < len(rec_scores) else 0.1
        final = alpha * c + beta * imp + gamma * t_score + delta * rc
        out.append((final, r))
    out.sort(key=lambda x: x[0], reverse=True)
    return out


def compute_final_scores_by_type(
    records: List[Dict],
    similarities: List[float],
    lam: float,
    type_weights: Dict[str, Dict[str, float]],
    default_weights: Dict[str, float],
    normalize: bool = True,
) -> List[Tuple[float, Dict]]:
    now_ts = int(time.time())
    scored: List[Tuple[float, Dict]] = []
    for i, r in enumerate(records):
        sim = float(similarities[i] if i < len(similarities) else float(r.get("similarity", 0.0) or 0.0))
        imp = float(r.get("importance", 0.0) or 0.0)
        ts = int(r.get("timestamp", now_ts) or now_ts)
        decay = temporal_score(ts, now_ts, lam)
        mtype = str(r.get("memory_type", "") or "")
        w = type_weights.get(mtype) or default_weights
        alpha = float(w.get("alpha", default_weights.get("alpha", 0.5)))
        beta = float(w.get("beta", default_weights.get("beta", 0.2)))
        theta = float(w.get("theta", default_weights.get("theta", 0.3)))
        final = alpha * sim + beta * imp + theta * decay
        r["_score"] = final
        r["_time_decay"] = decay
        scored.append((final, r))
    if normalize and scored:
        mx = max(x[0] for x in scored) or 1.0
        scored = [(x[0] / mx, {**x[1], "_score": x[0] / mx}) for x in scored]
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored
