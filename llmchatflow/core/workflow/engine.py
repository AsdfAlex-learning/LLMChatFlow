import time
from .base import WorkflowEngine
from ..llm.base import LLMClient
from ..session.base import ISession
from ..context.base import ContextBuilder
from ...utils.sqlite_helper import SQLiteMemoryStore
from ...utils.embedding import SimpleEmbedding


class SemanticMemoryEngine(WorkflowEngine):
    def __init__(
        self,
        session: ISession,
        llm_client: LLMClient,
        context_builder: ContextBuilder,
        store: SQLiteMemoryStore,
        embedder: SimpleEmbedding,
    ):
        self.session = session
        self.llm_client = llm_client
        self.context_builder = context_builder
        self.store = store
        self.embedder = embedder

    def process(self, user_input: str, **kwargs) -> str:
        session_id = self.session.session_id
        messages = self.context_builder.build_messages(session_id, user_input)
        reply = self.llm_client.chat_completion(messages)
        now_ts = int(time.time())
        user_emb = self.embedder.embed(user_input)
        self.store.insert_message(session_id, "user", user_input, user_emb, 0.9, now_ts)
        ai_emb = self.embedder.embed(reply)
        self.store.insert_message(session_id, "assistant", reply, ai_emb, 0.7, now_ts)
        return reply
