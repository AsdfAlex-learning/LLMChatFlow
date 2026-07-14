import logging
import math
import time
from typing import Any, Dict, List, Tuple

from .base import MemoryPolicy
from ..ranking import compute_final_scores_by_type

logger = logging.getLogger(__name__)


class DefaultMemoryPolicy(MemoryPolicy):
    """Default memory policy: type-aware scoring with configurable weights.

    Encapsulates FAISS recall -> type-aware scoring -> ranking,
    covering the most common retrieval scenarios out of the box.
    """

    def score(
        self,
        memory: Dict[str, Any],
        query_vector: List[float],
        **kwargs,
    ) -> float:
        """Score a single memory using type-aware weighting.

        Uses compute_final_scores_by_type with the memory's type-specific
        weights. Falls back to default weights for unknown types.
        """
        similarity = float(memory.get("similarity", 0.0))
        importance = float(memory.get("importance", 0.5))
        decay_rate = float(memory.get("decay_rate", 0.1))
        timestamp = int(memory.get("timestamp", 0))
        memory_type = str(memory.get("memory_type", "episodic"))

        # Use type weights from kwargs or defaults
        type_weights = kwargs.get("type_weights", {})
        default_weights = kwargs.get("default_weights", {"alpha": 0.5, "beta": 0.2, "theta": 0.3})
        lam = float(kwargs.get("lam", 0.1))

        # Compute temporal decay
        now = time.time()
        delta_days = max(0, (now - timestamp) / 86400) if timestamp else 0
        time_decay = math.exp(-lam * delta_days)

        weights = type_weights.get(memory_type, default_weights)
        alpha = float(weights.get("alpha", 0.5))
        beta = float(weights.get("beta", 0.2))
        theta = float(weights.get("theta", 0.3))

        score = alpha * similarity + beta * importance + theta * time_decay
        return max(0.0, score)

    def select(
        self,
        memories: List[Dict[str, Any]],
        query_vector: List[float],
        config: Any = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Select and rank memories using type-aware scoring.

        Steps:
        1. Compute scores for all memories using type-aware weighting
        2. Sort by score descending
        3. Apply keep_count limit
        4. Return ranked list with _score field set
        """
        if not memories:
            return []

        # Extract config params
        type_weights = {}
        default_weights = {"alpha": 0.5, "beta": 0.2, "theta": 0.3}
        lam = 0.1
        keep_count = 10
        normalize = True

        if config is not None:
            type_weights = {
                "episodic": getattr(config, "ranking_type_weights_episodic", {}),
                "habit": getattr(config, "ranking_type_weights_habit", {}),
                "summary": getattr(config, "ranking_type_weights_summary", {}),
            }
            default_weights = getattr(config, "ranking_type_weights_default", default_weights)
            lam = float(getattr(config, "ranking_lam", 0.1))
            keep_count = int(getattr(config, "ranking_keep_count", keep_count))
            normalize = bool(getattr(config, "ranking_score_normalize", normalize))

        # Override with kwargs if provided
        type_weights = kwargs.get("type_weights", type_weights)
        default_weights = kwargs.get("default_weights", default_weights)
        lam = float(kwargs.get("lam", lam))
        keep_count = int(kwargs.get("keep_count", keep_count))
        normalize = bool(kwargs.get("normalize", normalize))

        # Compute similarities list
        similarities = [float(m.get("similarity", 0.0)) for m in memories]

        # Use the existing ranking function for batch scoring
        scored = compute_final_scores_by_type(
            memories,
            similarities,
            lam=lam,
            type_weights=type_weights,
            default_weights=default_weights,
            normalize=normalize,
        )

        # Bucket-based selection: group by memory_type, allocate per-type quotas
        bucket_episodic = max(1, int(keep_count * 0.6))   # 60% episodic
        bucket_habit = max(0, int(keep_count * 0.3))       # 30% habit
        bucket_summary = max(0, keep_count - bucket_episodic - bucket_habit)

        # Group scored results by type
        buckets: Dict[str, List[Tuple[float, Dict]]] = {
            "episodic": [],
            "habit": [],
            "summary": [],
        }
        for entry in scored:
            s, rec = entry
            mtype = str(rec.get("memory_type", "episodic"))
            if mtype in buckets:
                buckets[mtype].append((s, rec))
            else:
                buckets["episodic"].append((s, rec))

        # Pick top-N from each bucket
        picked: List[Tuple[float, Dict]] = []
        bucket_limits = {
            "episodic": bucket_episodic,
            "habit": bucket_habit,
            "summary": bucket_summary,
        }
        for btype, limit in bucket_limits.items():
            bucket = sorted(buckets.get(btype, []), key=lambda x: x[0], reverse=True)
            picked.extend(bucket[:limit])

        # If under keep_count due to insufficient data, fill from remaining
        if len(picked) < keep_count:
            remaining: List[Tuple[float, Dict]] = []
            for btype in buckets:
                limit = bucket_limits[btype]
                remaining.extend(buckets[btype][limit:])
            remaining.sort(key=lambda x: x[0], reverse=True)
            filler_needed = keep_count - len(picked)
            picked.extend(remaining[:filler_needed])

        # Sort final result by score descending
        ranked = [r for _, r in sorted(picked, key=lambda x: x[0], reverse=True)]
        result = ranked

        logger.debug(
            "DefaultMemoryPolicy selected %d/%d memories (keep_count=%d, buckets: ep=%d, hab=%d, sum=%d)",
            len(result), len(memories), keep_count, bucket_episodic, bucket_habit, bucket_summary,
        )
        return result
