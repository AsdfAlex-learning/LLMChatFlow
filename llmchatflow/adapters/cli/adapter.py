import sys

class CLIAdapter:
    """Simple CLI Adapter for interaction."""

    def get_input(self, prompt: str = "User: ") -> str:
        try:
            return input(prompt)
        except EOFError:
            return ""

    def show_output(self, content: str) -> None:
        print(f"Assistant: {content}")
        print("-" * 20)

    def show_error(self, error: str) -> None:
        print(f"Error: {error}", file=sys.stderr)
