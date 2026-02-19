import time
from typing import List, Dict, Optional
from .base import ContextBuilder
from ..memory.storage import MemoryStore
from ...utils.embedding import SentenceEmbedding
from ..memory.semantic import semantic_scores
from ..memory.ranking import compute_final_scores
from ..memory.trimming import trim_records_to_token_budget
from ..prompt.assembler import SimplePromptAssembler


class StructuredContextBuilder(ContextBuilder):
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
        tokenizer_model: str = "BAAI/bge-small-zh-v1.5",
        top_k: int = 10,
    ):
        self.store = store
        self.embedder = embedder
        self.max_memory_token = max_memory_token
        self.lam = lam
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.delta = delta
        self.tokenizer_model = tokenizer_model
        self.top_k = top_k
        self.assembler = SimplePromptAssembler()

    def build_messages(
        self, session_id: str, user_text: str, current_embedding: Optional[List[float]] = None
    ) -> List[Dict[str, str]]:
        if current_embedding is None:
            current_embedding = self.embedder.embed(user_text)
        records = self.store.fetch_messages_by_session(session_id)
        cos = semantic_scores(current_embedding, records)
        scored = compute_final_scores(
            records,
            cos,
            lam=self.lam,
            alpha=self.alpha,
            beta=self.beta,
            gamma=self.gamma,
            delta=self.delta,
        )
        ranked = [r for _, r in scored][: self.top_k]
        for r in ranked:
            r["_score"] = float(r.get("_score", 0.0))
        trimmed = trim_records_to_token_budget(
            ranked, self.max_memory_token, self.tokenizer_model
        )
        trimmed.sort(key=lambda r: r.get("timestamp", 0))
        history_text = "\n".join([x["text"] for x in trimmed])
        messages = self.assembler.assemble(history_text, user_text)
        return messages
