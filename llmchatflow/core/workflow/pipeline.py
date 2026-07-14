from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import List, Optional, Protocol

from ..context.base import ContextBuilder
from ..llm.base import LLMClient
from ..memory.ranking import IMPORTANCE_AI_MSG, IMPORTANCE_USER_MSG
from ..memory.storage import MemoryStore
from ...utils.embedding import SentenceEmbedding

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """Shared state passed through the pipeline handler chain.

    Each handler reads and/or mutates this context as the pipeline progresses.
    """

    session_id: str
    user_input: str
    user_id: str = ""
    embedding: Optional[List[float]] = None
    retrieved_memories: Optional[List] = None
    messages: Optional[List] = None
    reply: Optional[str] = None


class Handler(Protocol):
    """Protocol for pipeline handler steps. Each handler mutates PipelineContext in-place."""

    def run(self, ctx: PipelineContext) -> None: ...


class EmbeddingHandler:
    """Pipeline step: embed user input into a vector."""

    def __init__(self, embedder: SentenceEmbedding):
        self.embedder = embedder

    def run(self, ctx: PipelineContext) -> None:
        """Embed the user input and store the vector in ctx.embedding."""
        ctx.embedding = self.embedder.embed(ctx.user_input)
        logger.info("Embedding done")


class RetrievalHandler:
    """Pipeline step: retrieve memories and build structured context messages."""

    def __init__(self, context_builder: ContextBuilder):
        self.context_builder = context_builder

    def run(self, ctx: PipelineContext) -> None:
        """Retrieve memories and build LLM-ready message list via ContextBuilder."""
        ctx.messages = self.context_builder.build_messages(
            ctx.session_id, ctx.user_input, current_embedding=ctx.embedding
        )
        ctx.retrieved_memories = ctx.messages
        logger.info("Retrieval done")


class LLMHandler:
    """Pipeline step: call LLM with context messages and store reply."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def run(self, ctx: PipelineContext) -> None:
        """Call the LLM with context messages and store the reply."""
        ctx.reply = self.llm_client.chat_completion(ctx.messages or [])
        logger.info("LLM done")


class StorageHandler:
    """Pipeline step: persist user input and assistant reply to memory store."""

    def __init__(self, store: MemoryStore, embedder: SentenceEmbedding):
        self.store = store
        self.embedder = embedder

    def run(self, ctx: PipelineContext) -> None:
        """Persist user input and assistant reply as paired memory records."""
        import uuid

        ts = time.time()
        now_ts = int(ts)
        turn_id = str(uuid.uuid4())
        self.store.insert_message(
            ctx.session_id,
            "user",
            ctx.user_input,
            ctx.embedding or [],
            IMPORTANCE_USER_MSG,  # user messages get higher default importance
            now_ts,
            user_id=ctx.user_id,
            turn_id=turn_id,
            memory_type="episodic",
            memory_scope="session",
            decay_rate=0.1,
        )
        ai_emb = self.embedder.embed(ctx.reply or "")
        if ai_emb is None:
            ai_emb = []
        self.store.insert_message(
            ctx.session_id,
            "assistant",
            ctx.reply or "",
            ai_emb,
            IMPORTANCE_AI_MSG,  # assistant messages get lower default importance
            now_ts,
            user_id=ctx.user_id,
            turn_id=turn_id,
            memory_type="episodic",
            memory_scope="session",
            decay_rate=0.1,
        )
        logger.info("Storage done (turn_id=%s)", turn_id)


class Pipeline:
    """Sequential pipeline that runs a chain of Handler steps on a shared PipelineContext.

    Supports early stopping (headless mode) via stop_before parameter.
    """

    def __init__(self, handlers: List[Handler]):
        self.handlers = handlers

    def run(self, ctx: PipelineContext, stop_before: type = None) -> PipelineContext:
        """Execute all handlers sequentially. Stops early if a handler matches stop_before type."""
        for h in self.handlers:
            if stop_before and isinstance(h, stop_before):
                logger.info("Pipeline stopped before %s (headless mode)", stop_before.__name__)
                break
            h.run(ctx)
        return ctx
