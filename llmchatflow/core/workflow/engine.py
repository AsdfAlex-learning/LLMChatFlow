import logging
import time
from typing import Any, Dict, Optional
from ..llm.base import LLMClient
from ..session.base import ISession
from ..context.base import ContextBuilder
from ..memory.storage import MemoryStore
from ..memory.manager import MemoryManager
from ...utils.embedding import SentenceEmbedding
from .pipeline import Pipeline, PipelineContext, EmbeddingHandler, RetrievalHandler, LLMHandler, StorageHandler

logger = logging.getLogger(__name__)


class SemanticMemoryEngine:
    """Top-level orchestrator for the memory-augmented conversation workflow.

    Supports two modes:
    - "full": Embed -> Retrieve -> LLM generate -> Store (complete chat cycle)
    - "headless": Embed -> Retrieve only (no LLM, returns structured data)

    Delegates to Pipeline for step execution and MemoryManager for headless retrieval.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        context_builder: ContextBuilder,
        store: MemoryStore,
        embedder: SentenceEmbedding,
        session: Optional[ISession] = None,
        mode: str = "full",
        memory_manager: Optional[MemoryManager] = None,
    ):
        self.session = session
        self.mode = mode
        self.memory_manager = memory_manager
        self.pipeline = Pipeline(
            [
                EmbeddingHandler(embedder),
                RetrievalHandler(context_builder),
                LLMHandler(llm_client),
                StorageHandler(store, embedder),
            ]
        )

    def process(self, user_input: str, **kwargs) -> str:
        """Run a full conversation turn: embed → retrieve → generate → store.

        Args:
            user_input: The raw user query text.
            **kwargs: Additional context (e.g., user_id).

        Returns:
            The LLM-generated reply text, or empty string on failure.

        Raises:
            RuntimeError: If session is not set (None).
        """
        if self.session is None:
            raise RuntimeError("SemanticMemoryEngine.session is not set. Set engine.session = session before calling process().")
        t0 = time.time()
        session_id = self.session.session_id
        logger.info("Workflow start (session_id=%s, mode=%s)", session_id, self.mode)
        ctx = PipelineContext(session_id=session_id, user_input=user_input, user_id=kwargs.get("user_id", ""))
        stop_before = LLMHandler if self.mode == "headless" else None
        ctx = self.pipeline.run(ctx, stop_before=stop_before)
        logger.info("Workflow done (session_id=%s, latency_ms=%d)", session_id, int((time.time() - t0) * 1000))
        return ctx.reply or ""

    def retrieve(self, user_input: str, **kwargs) -> Any:
        """Headless retrieval.

        If memory_manager is configured, uses MemoryManager.retrieve()
        which returns structured dict with memories/turns/latency.
        Otherwise falls back to pipeline (returns PipelineContext).

        Raises:
            RuntimeError: If session is not set (None).
        """
        if self.session is None:
            raise RuntimeError("SemanticMemoryEngine.session is not set. Set engine.session = session before calling retrieve().")
        session_id = self.session.session_id
        user_id = kwargs.get("user_id", "")

        if self.memory_manager is not None:
            logger.info("Headless retrieval via MemoryManager (session_id=%s)", session_id)
            config = kwargs.get("config")
            return self.memory_manager.retrieve(
                query=user_input,
                user_id=user_id,
                session_id=session_id,
                config=config,
            )

        logger.info("Headless retrieval via pipeline (session_id=%s)", session_id)
        ctx = PipelineContext(session_id=session_id, user_input=user_input, user_id=user_id)
        ctx = self.pipeline.run(ctx, stop_before=LLMHandler)
        return ctx
