"""Query Rewrite Module.

Handles optional query rewriting before embedding and retrieval.
Trigger modes: none (disabled), always (rewrite every query),
timed (rewrite if N seconds since last), count (rewrite every N turns).

Per plan Section 6.1 Step 2.
"""
import logging
import time
from typing import Optional

from ..llm.base import LLMClient

logger = logging.getLogger(__name__)

REWRITE_PROMPT = (
    "请将以下用户输入改写得更加清晰、完整，便于检索相关记忆。"
    "保留原始意图和关键信息，去除口语化冗余。\n\n用户输入：{text}\n\n改写结果："
)


class QueryRewriter:
    """Query rewriting with configurable trigger strategy."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        trigger: str = "none",
        persist: str = "none",
        interval_seconds: int = 300,
        interval_turns: int = 5,
    ):
        self.llm_client = llm_client
        self.trigger = trigger
        self.persist = persist
        self.interval_seconds = interval_seconds
        self.interval_turns = interval_turns
        self._last_rewrite_time: float = 0.0
        self._rewrite_count: int = 0

    def should_rewrite(self) -> bool:
        """Check whether a rewrite should be triggered per the configured strategy.

        Modes: 'always' → every query; 'timed' → after interval_seconds;
        'count' → every N turns; 'none' → never.
        """
        if self.trigger == "always":
            return True
        if self.trigger == "timed":
            return (time.time() - self._last_rewrite_time) >= self.interval_seconds
        if self.trigger == "count":
            self._rewrite_count += 1
            return self._rewrite_count % self.interval_turns == 0
        return False

    def rewrite(self, text: str) -> str:
        """Rewrite the query for clarity if should_rewrite() returns True.

        Falls back to the original text if LLM is unavailable or rewrite fails.
        """
        if not self.should_rewrite() or self.llm_client is None:
            return text
        try:
            prompt = REWRITE_PROMPT.format(text=text)
            result = self.llm_client.chat_completion(
                [{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=256,
            )
            result = result.strip().strip('"').strip("'")
            self._last_rewrite_time = time.time()
            logger.info("Query rewritten: '%s' -> '%s'", text[:50], result[:50])
            return result
        except Exception as e:
            logger.warning("Query rewrite failed, using original (%s)", str(e))
            return text
