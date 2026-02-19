import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llmchatflow.core.llm.openai_compatible import OpenAICompatibleClient
from llmchatflow.core.session.local import LocalSession
from llmchatflow.core.context.structured import StructuredContextBuilder
from llmchatflow.core.workflow.engine import SemanticMemoryEngine
from llmchatflow.adapters.cli.adapter import CLIAdapter
from llmchatflow.utils.sqlite_helper import SQLiteMemoryStore
from llmchatflow.utils.embedding import SimpleEmbedding


def main():
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY in .env")
        return
    session = LocalSession("cli_session_001")
    llm_client = OpenAICompatibleClient()
    store = SQLiteMemoryStore("memory.db")
    embedder = SimpleEmbedding()
    ctx_builder = StructuredContextBuilder(
        store=store,
        embedder=embedder,
        max_memory_token=2000,
        lam=0.1,
        alpha=0.5,
        beta=0.2,
        gamma=0.15,
        delta=0.15,
        tokenizer_model="gpt2",
        top_k=10,
    )
    engine = SemanticMemoryEngine(
        session=session,
        llm_client=llm_client,
        context_builder=ctx_builder,
        store=store,
        embedder=embedder,
    )
    adapter = CLIAdapter()
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


if __name__ == "__main__":
    main()
