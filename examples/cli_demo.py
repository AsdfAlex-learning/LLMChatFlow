import os
import sys

try:
    from dotenv import load_dotenv
    from llmchatflow.config import load_config
    from llmchatflow.core.llm.openai_compatible import OpenAICompatibleClient
    from llmchatflow.core.session.local import LocalSession
    from llmchatflow.core.context.structured import StructuredContextBuilder
    from llmchatflow.core.workflow.engine import SemanticMemoryEngine
    from llmchatflow.adapters.cli.adapter import CLIAdapter
    from llmchatflow.utils.sqlite_faiss_memory_store import SQLiteFaissMemoryStore
    from llmchatflow.utils.embedding import SentenceEmbedding
    from llmchatflow.utils.logging_utils import configure_logging_from_config
except ImportError as e:
    print(f"Error: LLMChatFlow is not installed ({e}).", file=sys.stderr)
    print("Install with:  pip install -e .", file=sys.stderr)
    sys.exit(1)


def _build_engine(cfg, with_llm: bool = True):
    """Build engine with or without LLM client."""
    store = SQLiteFaissMemoryStore("memory.db")
    embedder = SentenceEmbedding()
    session = LocalSession("cli_session_001")

    if with_llm:
        llm_client = OpenAICompatibleClient()
    else:
        llm_client = None

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
    return engine, adapter


def _run_headless_mode(engine, adapter):
    """Run in headless mode: retrieve memories without LLM generation."""
    print("\nRunning in HEADLESS mode (no LLM). Demonstrating memory retrieval...")
    print("Type a query to search memories, or 'exit' to quit.")
    print("-" * 50)
    while True:
        user_input = adapter.get_input("Query: ")
        if user_input.lower() in ["exit", "quit", "q"]:
            break
        if not user_input.strip():
            continue
        try:
            result = engine.retrieve(user_input)
            memories = result.get("memories", [])
            print(f"Found {len(memories)} memories:")
            for m in memories[:5]:
                print(f"  [{m.get('memory_type', '?')}] (score={m.get('_score', 0):.3f}) {m.get('role', '?')}: {m.get('text', '')[:60]}...")
        except Exception as e:
            adapter.show_error(str(e))


def _run_chat_mode(engine, adapter):
    """Run in full chat mode with LLM generation."""
    print("Welcome to LLMChatFlow CLI Demo! (Type 'exit' to quit)")
    print("-" * 50)
    while True:
        user_input = adapter.get_input()
        if user_input.lower() in ["exit", "quit", "q"]:
            break
        if not user_input.strip():
            continue
        try:
            response = engine.process(user_input)
            adapter.show_output(response)
        except Exception as e:
            adapter.show_error(str(e))


def _build_engine(cfg, with_llm: bool = True):
    """Build engine with or without LLM client."""
    store = SQLiteFaissMemoryStore("memory.db")
    embedder = SentenceEmbedding()
    session = LocalSession("cli_session_001")

    if with_llm:
        llm_client = OpenAICompatibleClient()
    else:
        llm_client = None

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
    return engine


def _run_headless_mode(engine, adapter):
    """Run in headless mode: retrieve memories without LLM generation."""
    print("\nRunning in HEADLESS mode (no LLM). Demonstrating memory retrieval...")
    print("Type a query to search memories, or 'exit' to quit.")
    print("-" * 50)
    while True:
        user_input = adapter.get_input("Query: ")
        if user_input.lower() in ["exit", "quit", "q"]:
            break
        if not user_input.strip():
            continue
        try:
            result = engine.retrieve(user_input)
            memories = result.get("memories", [])
            print(f"Found {len(memories)} memories:")
            for m in memories[:5]:
                print(f"  [{m.get('memory_type', '?')}] (score={m.get('_score', 0):.3f}) {m.get('role', '?')}: {m.get('text', '')[:60]}...")
        except Exception as e:
            adapter.show_error(str(e))


def _run_chat_mode(engine, adapter):
    """Run in full chat mode with LLM generation."""
    print("Welcome to LLMChatFlow CLI Demo! (Type 'exit' to quit)")
    print("-" * 50)
    while True:
        user_input = adapter.get_input()
        if user_input.lower() in ["exit", "quit", "q"]:
            break
        if not user_input.strip():
            continue
        try:
            response = engine.process(user_input)
            adapter.show_output(response)
        except Exception as e:
            adapter.show_error(str(e))


def main():
    load_dotenv()
    cfg = load_config()
    configure_logging_from_config(cfg)

    has_api_key = bool(os.getenv("OPENAI_API_KEY"))

    if not has_api_key:
        print("WARNING: OPENAI_API_KEY not set. LLM chat mode is disabled.")
        print("You can still use headless memory retrieval mode.")
        print("Set OPENAI_API_KEY in .env to enable full chat mode.\n")

    engine = _build_engine(cfg, with_llm=has_api_key)
    adapter = CLIAdapter()

    if has_api_key:
        _run_chat_mode(engine, adapter)
    else:
        _run_headless_mode(engine, adapter)


if __name__ == "__main__":
    main()
