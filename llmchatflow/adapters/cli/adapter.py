import sys

class CLIAdapter:
    """Simple CLI Adapter for interaction."""

    def get_input(self, prompt: str = "User: ") -> str:
        """Read user input from stdin. Returns empty string on EOF."""
        try:
            return input(prompt)
        except EOFError:
            return ""

    def show_output(self, content: str) -> None:
        """Print assistant response to stdout."""
        print(f"Assistant: {content}")
        print("-" * 20)

    def show_error(self, error: str) -> None:
        """Print error message to stderr."""
        print(f"Error: {error}", file=sys.stderr)
