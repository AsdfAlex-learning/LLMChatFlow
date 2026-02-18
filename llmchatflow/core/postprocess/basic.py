from .base import PostProcessor


class BasicPostProcessor(PostProcessor):
    def run(self, text: str) -> str:
        return text.strip()
