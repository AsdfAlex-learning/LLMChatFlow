"""LLMChatFlow program entry point.

Usage:
    python -m llmchatflow          # Run CLI mode
    python -m llmchatflow api      # Start API server
"""
import os
import runpy
import sys


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        import uvicorn

        api_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "apps", "api_server.py")
        )
        ns = runpy.run_path(api_path)
        uvicorn.run(ns["app"], host="0.0.0.0", port=8000)
    else:
        cli_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "examples", "cli_demo.py")
        )
        runpy.run_path(cli_path, run_name="__main__")


if __name__ == "__main__":
    main()
