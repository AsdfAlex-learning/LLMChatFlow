from abc import ABC, abstractmethod


class PostProcessor(ABC):
    @abstractmethod
    def run(self, text: str) -> str:
        pass
