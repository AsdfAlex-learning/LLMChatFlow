import logging
import time
from typing import List, Dict, Optional, Any
from .base import ContextBuilder
from ..memory.storage import MemoryStore
from ...utils.embedding import SentenceEmbedding
from ..memory.semantic import semantic_scores
from ..memory.ranking import compute_final_scores, compute_final_scores_by_type
from ..prompt.token_budget import trim_records_to_token_budget
from ..prompt.assembler import StructuredPromptAssembler
from ...config import load_config

logger = logging.getLogger(__name__)


class StructuredContextBuilder(ContextBuilder):
    """Multi-source context builder that assembles LLM-ready message lists.

    Pipeline: FAISS search -> ranking/scoring -> token trimming -> block assembly.
    Falls back to session-based retrieval when FAISS is unavailable.
    """

    def __init__(
        self,
        store: MemoryStore,
        embedder: SentenceEmbedding,
        max_memory_token: int = 2000,
        lam: float = 0.1,
        alpha: float = 0.5,
        beta: float = 0.2,
        gamma: float = 0.15,
        delta: float = 0.15,
        llm_model_name: str = "gpt-3.5-turbo",
        top_k: int = 10,
        config: Optional[Any] = None,
    ):
        self.store = store
        self.embedder = embedder
        self.max_memory_token = max_memory_token
        self.lam = lam
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.delta = delta
        self.llm_model_name = llm_model_name
        self.top_k = top_k
        self.assembler = StructuredPromptAssembler()
        self._config = config or load_config()

    def build_messages(
        self,
        session_id: str,
        user_text: str,
        current_embedding: Optional[List[float]] = None,
    ) -> List[Dict[str, str]]:
        """Build a structured message list for the LLM conversation.

        Pipeline: embed query → FAISS search → multi-factor scoring → token
        trimming → structured block assembly. Falls back to session fetch + cosine
        similarity when FAISS is unavailable or embedding fails.

        Args:
            session_id: Current conversation session identifier.
            user_text: The raw user input text.
            current_embedding: Pre-computed embedding (if None, embeds user_text).

        Returns:
            List of {'role': str, 'content': str} message dicts ready for LLM.
        """
        current_embedding = self._get_or_embed(user_text, current_embedding)
        if current_embedding is None:
            return self._build_fallback_messages(session_id, user_text)

        records = self._search_memories(session_id, current_embedding)
        weight_mode = str(getattr(self._config, "ranking_weight_mode", "global"))
        ranked = self._rank_memories(records, current_embedding, weight_mode) if records else []
        max_token = int(getattr(self._config, "context_max_token", self.max_memory_token))
        trimmed = trim_records_to_token_budget(ranked, max_token, self.llm_model_name)
        trimmed.sort(key=lambda r: r.get("timestamp", 0))
        blocks = self._build_blocks(trimmed)
        return self.assembler.assemble(blocks, user_text)

    def _get_or_embed(
        self,
        user_text: str,
        current_embedding: Optional[List[float]],
    ) -> Optional[List[float]]:
        if current_embedding is None:
            current_embedding = self.embedder.embed(user_text)
        return current_embedding

    def _build_fallback_messages(
        self,
        session_id: str,
        user_text: str,
    ) -> List[Dict[str, str]]:
        logger.warning("Embedding failed, degrading to raw text (session=%s)", session_id)
        records = self.store.fetch_messages_by_session(session_id)
        if records:
            max_token = int(getattr(self._config, "context_max_token", self.max_memory_token))
            # Embedding unavailable — use zero vector so ranking relies on importance + temporal only
            fallback_dim = int(getattr(self._config, "embedding_dimension", 384))
            zero_emb = [0.0] * fallback_dim
            cos = semantic_scores(zero_emb, records)
            scored = compute_final_scores(
                records,
                cos,
                lam=self.lam,
                alpha=self.alpha,
                beta=self.beta,
                gamma=self.gamma,
                delta=self.delta,
            )
            ranked = [r for _, r in scored][:self.top_k]
            trimmed = trim_records_to_token_budget(ranked, max_token, self.llm_model_name)
            trimmed.sort(key=lambda r: r.get("timestamp", 0))
            blocks = {}
            memory_texts = [r["text"] for r in trimmed if r.get("text")]
            if memory_texts:
                blocks["retrieved_memories"] = "\n".join(memory_texts)
            blocks["history_summary"] = ""
            return self.assembler.assemble(blocks, user_text)
        return self.assembler.assemble({"history_summary": ""}, user_text)

    def _search_memories(
        self,
        session_id: str,
        current_embedding: List[float],
    ) -> List[Dict]:
        faiss_topk = int(getattr(self._config, "faiss_topk", self.top_k))
        filter_strategy = str(getattr(self._config, "faiss_filter_strategy", "global"))

        records: List[Dict] = []
        if hasattr(self.store, "search_records"):
            for attempt in range(2):
                try:
                    records = self.store.search_records(
                        session_id=session_id,
                        query_embedding=current_embedding,
                        top_k=faiss_topk,
                        filter_strategy=filter_strategy,
                    )
                    break
                except Exception as e:
                    if attempt == 0:
                        logger.warning(
                            "FAISS search failed, retrying (session=%s, err=%s)",
                            session_id,
                            str(e),
                        )
                    else:
                        logger.warning(
                            "FAISS search retry also failed (session=%s, err=%s)",
                            session_id,
                            str(e),
                        )
                        records = []

        if not records:
            records = self.store.fetch_messages_by_session(session_id)
            if records:
                cos = semantic_scores(current_embedding, records)
                for r, sim in zip(records, cos):
                    r["_similarity"] = sim
                for r in records:
                    r["_from_session_fallback"] = True

        return records

    def _rank_memories(
        self,
        records: List[Dict],
        current_embedding: List[float],
        weight_mode: str,
    ) -> List[Dict]:
        if not records:
            return []

        is_fallback = any(r.get("_from_session_fallback") for r in records)

        if is_fallback:
            limit = self.top_k
            sims = [float(r.get("_similarity", 0.0)) for r in records]
            scored = compute_final_scores(
                records,
                sims,
                lam=self.lam,
                alpha=self.alpha,
                beta=self.beta,
                gamma=self.gamma,
                delta=self.delta,
            )
        else:
            limit = int(getattr(self._config, "ranking_keep_count", self.top_k))
            sims = [float(r.get("similarity", 0.0) or 0.0) for r in records]
            if weight_mode == "by_memory_type":
                type_weights = {
                    "episodic": getattr(self._config, "ranking_type_weights_episodic", {}),
                    "habit": getattr(self._config, "ranking_type_weights_habit", {}),
                    "summary": getattr(self._config, "ranking_type_weights_summary", {}),
                }
                default_weights = getattr(self._config, "ranking_type_weights_default", {})
                normalize = bool(getattr(self._config, "ranking_score_normalize", True))
                scored = compute_final_scores_by_type(
                    records,
                    sims,
                    lam=self.lam,
                    type_weights=type_weights,
                    default_weights=default_weights,
                    normalize=normalize,
                )
            else:
                scored = compute_final_scores(
                    records,
                    sims,
                    lam=self.lam,
                    alpha=self.alpha,
                    beta=self.beta,
                    gamma=self.gamma,
                    delta=self.delta,
                )

        ranked = [r for _, r in scored][:limit]
        for r in ranked:
            r.pop("_similarity", None)
            r.pop("_from_session_fallback", None)
            r["_score"] = float(r.get("_score", 0.0))

        return ranked

    def _build_blocks(self, trimmed: List[Dict]) -> Dict[str, str]:
        blocks = {}

        system_prompt = str(getattr(self._config, "system_prompt", ""))
        if system_prompt and system_prompt != "built-in":
            blocks["system_prompt"] = system_prompt

        memory_texts = [r["text"] for r in trimmed if r.get("text")]
        if memory_texts:
            blocks["retrieved_memories"] = "\n".join(memory_texts)

        # History summary (placeholder — full summarization comes in later commit)
        # When history_summarize is implemented, this block will contain compressed older turns
        blocks["history_summary"] = ""

        return blocks
