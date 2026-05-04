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
    def __init__(
        self,
        session: ISession,
        llm_client: LLMClient,
        context_builder: ContextBuilder,
        store: MemoryStore,
        embedder: SentenceEmbedding,
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
        """
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
