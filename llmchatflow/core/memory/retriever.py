import logging
import time
from typing import Any, Dict, List, Optional, Sequence

from .policy.base import MemoryPolicy
from .policy.default import DefaultMemoryPolicy
from .storage import MemoryStore
from .semantic import semantic_scores
from .ranking import compute_final_scores, compute_final_scores_by_type
from ...utils.embedding import SentenceEmbedding

logger = logging.getLogger(__name__)


class MemoryRetriever:
    """Orchestrates the memory retrieval pipeline.

    Handles: Embed query -> FAISS search -> SQLite metadata fetch -> Policy scoring/ranking.
    Supports both Filter First and Recall First strategies.
    """

    def __init__(
        self,
        store: MemoryStore,
        embedder: SentenceEmbedding,
        policy: Optional[MemoryPolicy] = None,
    ):
        self.store = store
        self.embedder = embedder
        self.policy = policy or DefaultMemoryPolicy()

    def retrieve(
        self,
        query: str,
        session_id: str,
        user_id: str = "",
        config: Any = None,
        policy: Optional[MemoryPolicy] = None,
    ) -> Dict[str, Any]:
        """Retrieve memories for a query.

        Args:
            query: The user's input text.
            session_id: Current session ID for filtering.
            user_id: Current user ID.
            config: AppConfig for parameter-driven behavior.
            policy: Override policy for this call (uses default if None).

        Returns:
            Dict with keys:
              "memories": List[Dict] — ranked memory records with _score
              "turns": List[List[Dict]] — memories grouped by turn_id
              "latency_ms": int — retrieval latency
        """
        t0 = time.time()
        active_policy = policy or self.policy

        # Step 1: Embed query
        query_embedding = self.embedder.embed(query)
        if query_embedding is None:
            logger.warning("Embedding failed in retriever, using zero vector")
            dim = int(getattr(config, "embedding_dimension", 384)) if config else 384
            query_embedding = [0.0] * dim

        # Step 2: FAISS search with strategy
        top_k = int(getattr(config, "faiss_topk", 20)) if config else 20
        filter_strategy = str(getattr(config, "faiss_filter_strategy", "global")) if config else "global"

        records: List[Dict[str, Any]] = []
        if hasattr(self.store, "search_records"):
            try:
                records = self.store.search_records(
                    session_id=session_id,
                    query_embedding=query_embedding,
                    top_k=top_k,
                    filter_strategy=filter_strategy,
                )
            except Exception as e:
                logger.warning("FAISS search failed, falling back to session fetch (%s)", str(e))
                records = []

        # Step 3: Fallback to session-based retrieval if FAISS returns nothing
        if not records:
            try:
                records = self.store.fetch_messages_by_session(session_id)
                if records and query_embedding:
                    cos = semantic_scores(query_embedding, records)
                    scored = compute_final_scores(
                        records, cos, lam=0.1, alpha=0.5, beta=0.2, gamma=0.15, delta=0.15,
                    )
                    records = [r for _, r in scored][:top_k]
            except Exception as e:
                logger.warning("Session fallback retrieval failed (%s)", str(e))
                records = []

        # Step 4: Apply policy for scoring and selection
        ranked = active_policy.select(records, query_embedding, config=config)

        # Step 5: Group by turn_id for turn-level reconstruction
        turns = self._group_by_turn(ranked)

        latency = int((time.time() - t0) * 1000)
        logger.info(
            "Retrieval done: %d memories, %d turns, latency_ms=%d (session=%s)",
            len(ranked), len(turns), latency, session_id,
        )

        return {
            "memories": ranked,
            "turns": turns,
            "latency_ms": latency,
        }

    def _group_by_turn(self, memories: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group memories by turn_id and sort turns chronologically.

        Within each turn, messages are sorted by role (user before assistant).
        Turns are sorted by the earliest timestamp in the turn.
        """
        turn_map: Dict[str, List[Dict[str, Any]]] = {}
        for m in memories:
            turn_id = str(m.get("turn_id", "") or "unknown")
            if turn_id not in turn_map:
                turn_map[turn_id] = []
            turn_map[turn_id].append(m)

        # Sort messages within each turn: user first, then assistant
        role_order = {"user": 0, "assistant": 1, "system": 2}
        for tid in turn_map:
            turn_map[tid].sort(key=lambda m: role_order.get(m.get("role", ""), 99))

        # Sort turns by earliest timestamp
        def turn_sort_key(turn: List[Dict]) -> int:
            timestamps = [int(m.get("timestamp", 0)) for m in turn if m.get("timestamp")]
            return min(timestamps) if timestamps else 0

        sorted_turns = sorted(turn_map.values(), key=turn_sort_key)
        return sorted_turns
