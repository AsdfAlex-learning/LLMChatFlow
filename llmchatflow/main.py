"""LLMChatFlow program entry point.

Usage:
    python -m llmchatflow          # Run CLI mode
    python -m llmchatflow api      # Start API server
"""
import sys


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        # Start API server
        from apps.api_server import app
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        # Run CLI demo
        from examples.cli_demo import main as cli_main

        sys.exit(cli_main())


if __name__ == "__main__":
    main()
