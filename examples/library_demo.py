"""Library Demo: demonstrates LLMChatFlow as a Python library.

Usage:
    python examples/library_demo.py

This example shows minimal initialization, session creation,
and one request processing flow per plan Section 3.1.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from llmchatflow.config import load_config
from llmchatflow.core.context.structured import StructuredContextBuilder
from llmchatflow.core.llm.openai_compatible import OpenAICompatibleClient
from llmchatflow.core.session.local import LocalSession
from llmchatflow.core.workflow.engine import SemanticMemoryEngine
from llmchatflow.utils.embedding import SentenceEmbedding
from llmchatflow.utils.sqlite_faiss_memory_store import SQLiteFaissMemoryStore
from llmchatflow.utils.logging_utils import configure_logging_from_config


def main() -> None:
    # Load config (reads config.yaml by default)
    config = load_config()
    configure_logging_from_config(config)

    # Initialize core components
    store = SQLiteFaissMemoryStore("demo_memory.db")
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
        top_k=config.ranking_keep_count,
    )

    # Create session and engine
    session = LocalSession("demo_session")
    engine = SemanticMemoryEngine(
        session=session,
        llm_client=llm_client,
        context_builder=ctx_builder,
        store=store,
        embedder=embedder,
    )

    # Process a request
    print("Sending: 你好，请介绍一下你自己")
    response = engine.process("你好，请介绍一下你自己")
    print(f"Response: {response}")

    # Second turn with memory
    print("\nSending: 我刚才问了什么？")
    response = engine.process("我刚才问了什么？")
    print(f"Response: {response}")

    print("\nLibrary demo completed successfully.")


if __name__ == "__main__":
    main()
