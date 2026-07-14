import os
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from llmchatflow.adapters.api.adapter import APIAdapter
from llmchatflow.config import load_config
from llmchatflow.core.context.structured import StructuredContextBuilder
from llmchatflow.core.llm.openai_compatible import OpenAICompatibleClient
from llmchatflow.core.session.local import LocalSession
from llmchatflow.core.workflow.engine import SemanticMemoryEngine
from llmchatflow.utils.embedding import SentenceEmbedding
from llmchatflow.utils.sqlite_faiss_memory_store import SQLiteFaissMemoryStore
from llmchatflow.utils.logging_utils import configure_logging_from_config

MAX_INPUT_LENGTH = 10000  # Maximum user input length in characters
RATE_LIMIT_WINDOW = 60  # Rate limit window in seconds
RATE_LIMIT_MAX_REQUESTS = 30  # Max requests per window per client


class RateLimiter:
    """Simple in-memory rate limiter using sliding window."""

    def __init__(self, max_requests: int = RATE_LIMIT_MAX_REQUESTS, window: int = RATE_LIMIT_WINDOW):
        self._max = max_requests
        self._window = window
        self._requests: Dict[str, list] = {}

    def check(self, client_id: str) -> bool:
        """Return True if request is allowed, False if rate limited."""
        now = time.time()
        if client_id not in self._requests:
            self._requests[client_id] = []
        # Prune old entries
        self._requests[client_id] = [t for t in self._requests[client_id] if now - t < self._window]
        if len(self._requests[client_id]) >= self._max:
            return False
        self._requests[client_id].append(now)
        return True


@asynccontextmanager
async def lifespan(application: FastAPI):
    # --- Startup: initialize singleton components once ---
    config = load_config()
    configure_logging_from_config(config)

    store = SQLiteFaissMemoryStore("data/memory.db")
    embedder = SentenceEmbedding(
        model_name=config.embedding_model,
        device=config.embedding_device or None,
    )
    llm_client = OpenAICompatibleClient(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL"),
        model=os.environ.get("LLM_MODEL", "gpt-3.5-turbo"),
    )
    ctx_builder = StructuredContextBuilder(
        store=store,
        embedder=embedder,
        max_memory_token=config.context_max_token,
        lam=0.1,
        alpha=0.5,
        beta=0.2,
        gamma=0.15,
        delta=0.15,
        llm_model_name=os.environ.get("LLM_MODEL", "gpt-3.5-turbo"),
        top_k=config.ranking_keep_count,
    )
    engine = SemanticMemoryEngine(
        session=None,  # session is per-request, set at call time
        llm_client=llm_client,
        context_builder=ctx_builder,
        store=store,
        embedder=embedder,
    )

    # Readiness checks state
    application.state.ready_checks = {
        "fastapi": True,
        "sqlite_store": True,
        "embedding_model": True,
        "openai_key": bool(os.environ.get("OPENAI_API_KEY")),
    }

    application.state.config = config
    application.state.store = store
    application.state.embedder = embedder
    application.state.llm_client = llm_client
    application.state.ctx_builder = ctx_builder
    application.state.engine = engine
    application.state.rate_limiter = RateLimiter()

    yield  # app is running

    # --- Shutdown: cleanup resources ---
    store.close()


app = FastAPI(title="LLMChatFlow API", lifespan=lifespan)
api_adapter = APIAdapter()


class ChatRequest(BaseModel):
    session_id: str = "default_session"
    user_input: str = Field(..., max_length=MAX_INPUT_LENGTH)


class ChatResponse(BaseModel):
    response: str


def _check_rate_limit(request: Request) -> None:
    """Raise 429 if client exceeds rate limit."""
    limiter: RateLimiter = app.state.rate_limiter
    client_id = request.client.host if request.client else "unknown"
    if not limiter.check(client_id):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_MAX_REQUESTS} requests per {RATE_LIMIT_WINDOW}s.",
        )


@app.get("/health")
def health():
    """Liveness probe — returns 200 if the process is running."""
    return {"status": "ok"}


@app.get("/ready")
def ready() -> Dict[str, Any]:
    """Readiness probe — returns 200 only if all dependencies are healthy."""
    checks: Dict[str, bool] = app.state.ready_checks
    all_ok = all(checks.values())
    if not all_ok:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "checks": checks,
                "message": "Some dependencies are not ready. Set OPENAI_API_KEY for full mode, or use headless endpoints.",
            },
        )
    return {"status": "ready", "checks": checks}


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    _check_rate_limit(request)
    parsed = api_adapter.parse_request(payload.model_dump())
    if not parsed["user_input"].strip():
        raise HTTPException(status_code=400, detail="user_input is required")

    # Graceful fallback: if no API key, return a clear error instead of crashing mid-request
    if not app.state.ready_checks["openai_key"]:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured. Set it as an environment variable to use the chat endpoint, or use /retrieve for headless memory retrieval.",
        )

    # Per-request session passed as parameter — thread-safe, no shared mutable state
    session = LocalSession(parsed["session_id"])
    engine: SemanticMemoryEngine = app.state.engine

    response_text = engine.process(parsed["user_input"], session=session)
    formatted = api_adapter.format_response(response_text)
    return ChatResponse(**formatted)


@app.post("/retrieve")
def retrieve(payload: ChatRequest, request: Request) -> Dict[str, Any]:
    """Headless memory retrieval — does not require OPENAI_API_KEY."""
    _check_rate_limit(request)
    parsed = api_adapter.parse_request(payload.model_dump())
    if not parsed["user_input"].strip():
        raise HTTPException(status_code=400, detail="user_input is required")

    session = LocalSession(parsed["session_id"])
    engine: SemanticMemoryEngine = app.state.engine

    result = engine.retrieve(
        parsed["user_input"],
        session=session,
        user_id=parsed.get("user_id", ""),
        config=app.state.config,
    )
    return result
