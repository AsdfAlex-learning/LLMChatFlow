from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Protocol

from ..context.base import ContextBuilder
from ..llm.base import LLMClient
from ..session.base import ISession
from ..memory.storage import MemoryStore
from ...utils.embedding import SentenceEmbedding

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    session_id: str
    user_input: str
    embedding: Optional[List[float]] = None
    retrieved_memories: Optional[List] = None
    messages: Optional[List] = None
    reply: Optional[str] = None


class Handler(Protocol):
    def run(self, ctx: PipelineContext) -> None: ...


class EmbeddingHandler:
    def __init__(self, embedder: SentenceEmbedding):
        self.embedder = embedder

    def run(self, ctx: PipelineContext) -> None:
        ctx.embedding = self.embedder.embed(ctx.user_input)
        logger.info("Embedding done")


class RetrievalHandler:
    def __init__(self, context_builder: ContextBuilder):
        self.context_builder = context_builder

    def run(self, ctx: PipelineContext) -> None:
        ctx.messages = self.context_builder.build_messages(
            ctx.session_id, ctx.user_input, current_embedding=ctx.embedding
        )
        logger.info("Retrieval done")


class LLMHandler:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def run(self, ctx: PipelineContext) -> None:
        ctx.reply = self.llm_client.chat_completion(ctx.messages or [])
        logger.info("LLM done")


class StorageHandler:
    def __init__(self, store: MemoryStore, embedder: SentenceEmbedding):
        self.store = store
        self.embedder = embedder

    def run(self, ctx: PipelineContext) -> None:
        ts = __import__("time").time()
        now_ts = int(ts)
        self.store.insert_message(
            ctx.session_id,
            "user",
            ctx.user_input,
            ctx.embedding or [],
            0.9,
            now_ts,
            MTEW=0.8,
            MTEW_decay=0.1,
        )
        ai_emb = self.embedder.embed(ctx.reply or "")
        self.store.insert_message(
            ctx.session_id,
            "assistant",
            ctx.reply or "",
            ai_emb,
            0.7,
            now_ts,
            MTEW=0.8,
            MTEW_decay=0.1,
        )
        logger.info("Storage done")


class Pipeline:
    def __init__(self, handlers: List[Handler]):
        self.handlers = handlers

    def run(self, ctx: PipelineContext) -> PipelineContext:
        for h in self.handlers:
            h.run(ctx)
        return ctx
