import logging
import time
from ..llm.base import LLMClient
from ..session.base import ISession
from ..context.base import ContextBuilder
from ..memory.storage import MemoryStore
from ...utils.embedding import SentenceEmbedding

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
        self.llm_client = llm_client
        self.context_builder = context_builder
        self.store = store
        self.embedder = embedder

    def process(self, user_input: str, **kwargs) -> str:
        t0 = time.time()
        session_id = self.session.session_id
        logger.info("Workflow start (session_id=%s)", session_id)
        user_emb = self.embedder.embed(user_input)
        messages = self.context_builder.build_messages(
            session_id, user_input, current_embedding=user_emb
        )
        reply = self.llm_client.chat_completion(messages)
        now_ts = int(time.time())
        self.store.insert_message(
            session_id,
            "user",
            user_input,
            user_emb,
            0.9,
            now_ts,
            MTEW=0.8,
            MTEW_decay=0.1,
        )
        ai_emb = self.embedder.embed(reply)
        self.store.insert_message(
            session_id,
            "assistant",
            reply,
            ai_emb,
            0.7,
            now_ts,
            MTEW=0.8,
            MTEW_decay=0.1,
        )
        logger.info("Workflow done (session_id=%s, latency_ms=%d)", session_id, int((time.time() - t0) * 1000))
        return reply
