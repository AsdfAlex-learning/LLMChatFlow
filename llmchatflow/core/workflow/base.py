from abc import ABC, abstractmethod
from typing import Any

class WorkflowEngine(ABC):
    """Abstract base class for Workflow Engine."""

    @abstractmethod
    def process(self, user_input: str, **kwargs) -> str:
        """Process user input and return response."""
        pass
