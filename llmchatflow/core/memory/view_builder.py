import logging
from typing import Any, Dict, List, Optional

from ..prompt.token_budget import trim_records_to_token_budget
from ...utils.token_counter import count_tokens

logger = logging.getLogger(__name__)


class MemoryViewBuilder:
    """Converts retrieval results into different output formats.

    Handles the presentation layer: retrieval results (structured data)
    are transformed into text, prompt, or structured views based on
    downstream needs. Token-aware formatting ensures output stays
    within budget.
    """

    def __init__(self, model: str = "gpt-3.5-turbo", max_tokens: int = 2000):
        self.model = model
        self.max_tokens = max_tokens

    def build_view(
        self,
        retrieval_result: Dict[str, Any],
        format: str = "structured",
        max_tokens: Optional[int] = None,
    ) -> Any:
        """Build a view of retrieval results in the specified format.

        Args:
            retrieval_result: Dict from MemoryRetriever.retrieve() with
                "memories" and "turns" keys.
            format: Output format -- "text", "prompt", or "structured".
            max_tokens: Override max token budget for this call.

        Returns:
            - "text": Formatted human-readable string
            - "prompt": String suitable for LLM injection
            - "structured": Dict with memories and turns (default)
        """
        memories = retrieval_result.get("memories", [])
        turns = retrieval_result.get("turns", [])
        budget = max_tokens or self.max_tokens

        if format == "structured":
            return self._build_structured(memories, turns)
        elif format == "text":
            return self._build_text(memories, turns, budget)
        elif format == "prompt":
            return self._build_prompt(memories, turns, budget)
        else:
            logger.warning("Unknown view format '%s', falling back to structured", format)
            return self._build_structured(memories, turns)

    def _build_structured(
        self, memories: List[Dict], turns: List[List[Dict]]
    ) -> Dict[str, Any]:
        """Return structured dict with memories and turns."""
        return {
            "memories": [
                {
                    "id": m.get("id", m.get("uuid", "")),
                    "role": m.get("role", ""),
                    "text": m.get("text", ""),
                    "memory_type": m.get("memory_type", ""),
                    "importance": m.get("importance", 0.0),
                    "timestamp": m.get("timestamp", 0),
                    "score": m.get("_score", 0.0),
                }
                for m in memories
            ],
            "turns": [
                [
                    {
                        "role": m.get("role", ""),
                        "text": m.get("text", ""),
                        "timestamp": m.get("timestamp", 0),
                    }
                    for m in turn
                ]
                for turn in turns
            ],
        }

    def _build_text(
        self, memories: List[Dict], turns: List[List[Dict]], budget: int
    ) -> str:
        """Build a human-readable text view within token budget."""
        lines: List[str] = []
        for m in memories:
            role = m.get("role", "unknown")
            text = m.get("text", "")
            score = m.get("_score", 0.0)
            lines.append(f"[{role}] (score: {score:.3f}) {text}")

        full_text = "\n".join(lines)

        # Trim if over budget
        token_count = count_tokens(full_text, self.model)
        if token_count > budget and memories:
            trimmed = trim_records_to_token_budget(memories, budget, self.model)
            lines = [
                f"[{m.get('role', 'unknown')}] (score: {m.get('_score', 0.0):.3f}) {m.get('text', '')}"
                for m in trimmed
            ]
            full_text = "\n".join(lines)

        return full_text

    def _build_prompt(
        self, memories: List[Dict], turns: List[List[Dict]], budget: int
    ) -> str:
        """Build a prompt-ready text fragment within token budget.

        Format: chronological turn reconstruction for LLM context injection.
        """
        parts: List[str] = []

        # First, try turn-based reconstruction
        for turn in turns:
            turn_parts = []
            for m in turn:
                role = m.get("role", "unknown")
                text = m.get("text", "")
                turn_parts.append(f"{role}: {text}")
            parts.append("\n".join(turn_parts))

        # Fall back to flat memory list if no turns
        if not parts and memories:
            for m in memories:
                role = m.get("role", "unknown")
                text = m.get("text", "")
                parts.append(f"{role}: {text}")

        full_text = "\n---\n".join(parts)

        # Trim if over budget
        token_count = count_tokens(full_text, self.model)
        if token_count > budget and memories:
            trimmed = trim_records_to_token_budget(memories, budget, self.model)
            trimmed.sort(key=lambda r: r.get("timestamp", 0))
            parts = [
                f"{m.get('role', 'unknown')}: {m.get('text', '')}" for m in trimmed
            ]
            full_text = "\n".join(parts)

        return full_text
