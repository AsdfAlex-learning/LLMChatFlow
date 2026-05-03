import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from llmchatflow.adapters.api.adapter import APIAdapter
from llmchatflow.config import load_config
from llmchatflow.core.context.structured import StructuredContextBuilder
from llmchatflow.core.llm.openai_compatible import OpenAICompatibleClient
from llmchatflow.core.session.local import LocalSession
from llmchatflow.core.workflow.engine import SemanticMemoryEngine
from llmchatflow.utils.embedding import SentenceEmbedding
from llmchatflow.utils.sqlite_faiss_memory_store import SQLiteFaissMemoryStore
from llmchatflow.utils.logging_utils import configure_logging_from_config


@asynccontextmanager
async def lifespan(application: FastAPI):
    # --- Startup: initialize singleton components once ---
    config = load_config()
    configure_logging_from_config(config)

    store = SQLiteFaissMemoryStore("memory.db")
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

    application.state.config = config
    application.state.store = store
    application.state.embedder = embedder
    application.state.llm_client = llm_client
    application.state.ctx_builder = ctx_builder
    application.state.engine = engine

    yield  # app is running

    # --- Shutdown: cleanup if needed ---
    # SQLiteFaissMemoryStore and FAISS handles are released on process exit


app = FastAPI(title="LLMChatFlow API", lifespan=lifespan)
api_adapter = APIAdapter()


class ChatRequest(BaseModel):
    session_id: str = "default_session"
    user_input: str


class ChatResponse(BaseModel):
    response: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    parsed = api_adapter.parse_request(payload.model_dump())
    if not parsed["user_input"].strip():
        raise HTTPException(status_code=400, detail="user_input is required")

    # Lightweight per-request session; all heavy components are shared singletons
    session = LocalSession(parsed["session_id"])
    engine: SemanticMemoryEngine = app.state.engine
    engine.session = session

    response_text = engine.process(parsed["user_input"])
    formatted = api_adapter.format_response(response_text)
    return ChatResponse(**formatted)
