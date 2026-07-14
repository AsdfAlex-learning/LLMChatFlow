# Contributing to LLMChatFlow

Thanks for your interest in contributing. This guide covers how to set up the project, run tests, and submit changes.

## Getting Started

1.  **Clone the repository**

    ```bash
    git clone https://github.com/your-org/llmchatflow.git
    cd llmchatflow
    ```

2.  **Install in development mode**

    ```bash
    pip install -e ".[dev]"
    ```

3.  **Run the tests**

    ```bash
    pytest tests/ -v
    ```

## Development Workflow

1.  Create a new branch from `main` for your work
2.  Make your changes, keeping commits focused and atomic
3.  Run the test suite locally before pushing
4.  Open a pull request with a clear description of what changed and why
5.  Ensure CI passes and address any review feedback

## Code Style

- Follow existing patterns in the codebase. Consistency matters more than personal preference.
- Use ABCs to define interfaces for each subsystem (see `base.py` files in `core/` modules).
- Keep parameters config-driven through `AppConfig` instead of hardcoding values.
- Use lazy imports for heavy ML dependencies (sentence_transformers, transformers, faiss) at the module level.

## Commit Messages

Use the format `type(scope): description`

- **type**: `feat`, `fix`, `refactor`, `chore`, `test`, or `docs`
- **scope**: module name (e.g., `memory`, `retriever`, `api_server`)

Examples:

```
feat(memory): add importance decay to ranking
fix(api): handle missing API key gracefully
docs(readme): update quick start instructions
```

## Testing

- Quick feedback: `pytest tests/ -m "not slow"` (pure memory, about 60 seconds)
- Full suite: `pytest tests/` (includes FAISS and SQLite integration tests)
- With coverage: `pytest tests/ -m "not slow" --cov=llmchatflow --cov-report=term-missing`

Minimum 50% coverage is required for CI to pass.

## Architecture Notes

Refer to `AGENTS.md` for the full module structure and code map. Key points:

- The **Memory Intelligence Layer** (`core/memory/`) is the heart of the system. It coordinates policy, retrieval, ranking, and view building.
- **Configuration** is centralized in the `AppConfig` dataclass (`config/config.py`). All parameterized behavior should read from there.
- **Adapters** (`adapters/cli/`, `adapters/api/`) handle I/O formatting and should remain thin.
- Install the package via `pip install -e .` instead of using `sys.path.insert()` hacks.

## Anti-patterns to Avoid

- Do not hardcode `memory_type`, `importance`, `scope`, or `decay_rate` values. Pass them through config or parameters.
- Do not bypass the `MemoryStore` ABC to directly manipulate SQLite.
- Do not use `sys.path.insert()` to resolve imports. Rely on proper package installation.
