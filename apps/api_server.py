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

app = FastAPI(title="LLMChatFlow API")
api_adapter = APIAdapter()
configure_logging_from_config(load_config())


class ChatRequest(BaseModel):
    session_id: str = "default_session"
    user_input: str


class ChatResponse(BaseModel):
    response: str


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    parsed = api_adapter.parse_request(payload.model_dump())
    if not parsed["user_input"].strip():
        raise HTTPException(status_code=400, detail="user_input is required")
    session = LocalSession(parsed["session_id"])
    llm_client = OpenAICompatibleClient()
    store = SQLiteFaissMemoryStore("memory.db")
    embedder = SentenceEmbedding()
    ctx_builder = StructuredContextBuilder(
        store=store,
        embedder=embedder,
        max_memory_token=2000,
        lam=0.1,
        alpha=0.5,
        beta=0.2,
        gamma=0.15,
        delta=0.15,
        llm_model_name="gpt-3.5-turbo",
        top_k=10,
    )
    engine = SemanticMemoryEngine(
        session=session,
        llm_client=llm_client,
        context_builder=ctx_builder,
        store=store,
        embedder=embedder,
    )
    response_text = engine.process(parsed["user_input"])
    formatted = api_adapter.format_response(response_text)
    return ChatResponse(**formatted)
