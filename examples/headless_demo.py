"""Headless Demo: demonstrates memory-only retrieval without LLM.

Usage:
    python examples/headless_demo.py

This example shows the MemoryManager headless mode per plan Section 7.2/7.5:
embed -> search -> score -> select -> build_view, without any LLM call.

Requires LLMChatFlow to be installed: pip install -e .
"""
import os
import sys

try:
    from llmchatflow.config import load_config
    from llmchatflow.core.memory.manager import MemoryManager
    from llmchatflow.utils.embedding import SentenceEmbedding
    from llmchatflow.utils.sqlite_faiss_memory_store import SQLiteFaissMemoryStore
    from llmchatflow.utils.logging_utils import configure_logging_from_config
except ImportError as e:
    print(f"Error: LLMChatFlow is not installed ({e}).", file=sys.stderr)
    print("Install with:  pip install -e .", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    config = load_config()
    configure_logging_from_config(config)

    store = SQLiteFaissMemoryStore("headless_demo_memory.db")
    embedder = SentenceEmbedding(
        model_name=config.embedding_model,
        device=config.embedding_device or None,
    )

    # First, store some memories so we have data to retrieve
    print("Storing example memories...")
    import uuid
    import time

    tid = str(uuid.uuid4())
    ts = int(time.time())

    store.insert_message(
        session_id="headless_session",
        role="user",
        text="我喜欢Python编程",
        embedding=embedder.embed("我喜欢Python编程"),
        importance=0.8,
        timestamp=ts,
        turn_id=tid,
        user_id="user1",
        memory_type="habit",
        memory_scope="user",
        decay_rate=0.05,
    )
    store.insert_message(
        session_id="headless_session",
        role="assistant",
        text="Python是一门很适合初学者的语言",
        embedding=embedder.embed("Python是一门很适合初学者的语言"),
        importance=0.7,
        timestamp=ts,
        turn_id=tid,
        user_id="user1",
        memory_type="episodic",
        memory_scope="session",
        decay_rate=0.1,
    )
    print("Stored 2 memories.\n")

    # Create MemoryManager for headless retrieval
    manager = MemoryManager(store, embedder, model="gpt-3.5-turbo")

    # --- Headless retrieve: no LLM call ---
    query = "编程语言偏好"
    print(f"Query: {query}")
    result = manager.retrieve(
        query=query,
        user_id="user1",
        session_id="headless_session",
        config=config,
    )
    print(f"Found {len(result['memories'])} memories in {result['latency_ms']}ms")
    print(f"Grouped into {len(result['turns'])} turns")

    # --- Build views in different formats ---
    print("\n--- Structured view ---")
    view = manager.build_view(result, format="structured")
    for m in view["memories"]:
        print(f"  [{m['memory_type']}] (score={m['score']:.3f}) {m['role']}: {m['text'][:50]}")

    print("\n--- Text view ---")
    text_view = manager.build_view(result, format="text")
    print(text_view[:300])

    print("\n--- Prompt view ---")
    prompt_view = manager.build_view(result, format="prompt")
    print(prompt_view[:300])

    print("\nHeadless demo completed. No LLM was called!")


if __name__ == "__main__":
    main()
