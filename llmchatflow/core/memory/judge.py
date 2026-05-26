"""Memory Judge Module.

LLM-augmented judging for memory type classification and importance scoring.

Per plan Section 6.2 Steps 2-3: memory_type_llm_judge (True) -> LLM decides
habit/episodic/summary; importance_llm_judge (True) -> LLM scores importance.
"""
import json
import logging
from typing import Any, Dict, Optional

from ..llm.base import LLMClient

logger = logging.getLogger(__name__)

TYPE_JUDGE_PROMPT = (
    "分析以下用户输入，判断其记忆类型。只返回JSON，不要其他内容。\n"
    '格式: {{"memory_type": "...", "importance": 0.0-1.0, "reason": "..."}}\n'
    "记忆类型: episodic(对话片段), habit(用户偏好/习惯), summary(需要压缩总结)\n"
    "importance: 0.0(无关紧要) 到 1.0(极其重要)\n\n"
    "用户输入: {text}\n"
)

FALLBACK_TYPE = "episodic"
FALLBACK_IMPORTANCE = 0.5


class LLMJudge:
    """LLM-based memory type classifier and importance scorer."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        enable_type_judge: bool = True,
        enable_importance_judge: bool = True,
    ):
        self.llm_client = llm_client
        self.enable_type_judge = enable_type_judge
        self.enable_importance_judge = enable_importance_judge

    def judge(self, text: str, user_id: str = "") -> Dict[str, Any]:
        """Judge memory type and importance for the given text.

        Returns dict with keys: memory_type, importance.
        Falls back to defaults if LLM is unavailable or judging is disabled.
        """
        result: Dict[str, Any] = {}
        result["memory_type"] = FALLBACK_TYPE
        result["importance"] = FALLBACK_IMPORTANCE

        if not self.enable_type_judge and not self.enable_importance_judge:
            return result

        if self.llm_client is None:
            return result

        try:
            prompt = TYPE_JUDGE_PROMPT.format(text=text[:500])
            response = self.llm_client.chat_completion(
                [{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=128,
            )
            parsed = json.loads(response.strip())
            if self.enable_type_judge:
                mt = str(parsed.get("memory_type", FALLBACK_TYPE)).lower()
                if mt in ("episodic", "habit", "summary"):
                    result["memory_type"] = mt
            if self.enable_importance_judge:
                imp = float(parsed.get("importance", FALLBACK_IMPORTANCE))
                result["importance"] = max(0.0, min(1.0, imp))
            logger.debug(
                "LLM judge: type=%s, importance=%.2f (user=%s)",
                result["memory_type"], result["importance"], user_id,
            )
        except Exception as e:
            logger.warning("LLM judge failed, using defaults (%s)", str(e))

        return result
