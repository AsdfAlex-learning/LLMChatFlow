import logging
from typing import Any, Dict, Optional

from .policy.base import MemoryPolicy
from .policy.default import DefaultMemoryPolicy
from .retriever import MemoryRetriever
from .view_builder import MemoryViewBuilder
from .storage import MemoryStore
from ...utils.embedding import SentenceEmbedding

logger = logging.getLogger(__name__)


class MemoryManager:
    """Unified entry point for memory operations.

    Provides three core APIs:
    - retrieve(): Get memories for a query (headless-friendly)
    - store(): Save conversation to memory
    - build_view(): Convert retrieval results to different formats

    DefaultMemoryPolicy is used when no policy is explicitly provided.
    """

    def __init__(
        self,
        store: MemoryStore,
        embedder: SentenceEmbedding,
        policy: Optional[MemoryPolicy] = None,
        model: str = "gpt-3.5-turbo",
    ):
        self.store = store
        self.embedder = embedder
        self.policy = policy or DefaultMemoryPolicy()
        self.retriever = MemoryRetriever(store, embedder, self.policy)
        self.view_builder = MemoryViewBuilder(model=model)

    def retrieve(
        self,
        query: str,
        user_id: str = "",
        session_id: str = "",
        config: Any = None,
        policy: Optional[MemoryPolicy] = None,
    ) -> Dict[str, Any]:
        """Headless Retrieval API: embed -> search -> score -> select -> group.

        Returns structured data: {"memories": [...], "turns": [...], "latency_ms": N}.

        Per plan Section 7.9.4: returns structured data by default, not a forced prompt.
        Use build_view() to convert to prompt/text format when needed.
        """
        return self.retriever.retrieve(
            query=query,
            session_id=session_id,
            user_id=user_id,
            config=config,
            policy=policy,
        )

    def build_view(
        self,
        retrieval_result: Dict[str, Any],
        format: str = "structured",
        max_tokens: Optional[int] = None,
    ) -> Any:
        """View Builder API: convert retrieval results to text/prompt/structured.

        Args:
            retrieval_result: Result from retrieve().
            format: "structured" (default), "text", or "prompt".
            max_tokens: Override token budget for view.

        Returns:
            Varies by format. See MemoryViewBuilder.build_view().
        """
        return self.view_builder.build_view(
            retrieval_result=retrieval_result,
            format=format,
            max_tokens=max_tokens,
        )

    def store(
        self,
        user_input: str,
        response: str,
        session_id: str,
        user_id: str = "",
        turn_id: Optional[str] = None,
        config: Any = None,
    ) -> None:
        """Store a conversation turn into memory.

        Both user input and assistant response are stored as episodic memories
        with the same turn_id. Importance defaults are used (LLM Judge comes later).
        """
        import time
        import uuid

        tid = turn_id or str(uuid.uuid4())
        ts = int(time.time())

        importance = float(getattr(config, "importance_default", 0.5)) if config else 0.5

        user_emb = self.embedder.embed(user_input)
        self.store.insert_message(
            session_id=session_id,
            role="user",
            text=user_input,
            embedding=user_emb,
            importance=importance,
            timestamp=ts,
            user_id=user_id,
            turn_id=tid,
            memory_type="episodic",
            memory_scope="session",
            decay_rate=0.1,
        )

        if response:
            ai_emb = self.embedder.embed(response)
            self.store.insert_message(
                session_id=session_id,
                role="assistant",
                text=response,
                embedding=ai_emb,
                importance=importance,
                timestamp=ts,
                user_id=user_id,
                turn_id=tid,
                memory_type="episodic",
                memory_scope="session",
                decay_rate=0.1,
            )

        logger.info("MemoryManager stored turn (turn_id=%s, session=%s)", tid, session_id)
