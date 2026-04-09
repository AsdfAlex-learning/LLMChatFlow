import logging
import time
from ..llm.base import LLMClient
from ..session.base import ISession
from ..context.base import ContextBuilder
from ..memory.storage import MemoryStore
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
    ):
        self.session = session
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
        logger.info("Workflow start (session_id=%s)", session_id)
        ctx = PipelineContext(session_id=session_id, user_input=user_input)
        ctx = self.pipeline.run(ctx)
        logger.info("Workflow done (session_id=%s, latency_ms=%d)", session_id, int((time.time() - t0) * 1000))
        return ctx.reply or ""
