import logging
from typing import Dict, List
from .base import PromptTemplate

logger = logging.getLogger(__name__)


class StructuredPromptAssembler(PromptTemplate):
    """Assembles structured prompt messages from context blocks.

    Layout: [system] [history_summary] [retrieved_memories] [user].
    Empty blocks are omitted. Default system prompt is in Chinese.
    """

    def __init__(self, system_prompt: str = "你是一个有同理心且高效的助手。"):
        self.system_prompt = system_prompt

    def assemble(self, blocks: Dict[str, str], user_text: str) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []

        # Block 1: System prompt
        system_content = blocks.get("system_prompt", "") or self.system_prompt
        messages.append({"role": "system", "content": system_content})

        # Block 2: History summary (if non-empty)
        history_summary = blocks.get("history_summary", "")
        if history_summary and history_summary.strip():
            messages.append({
                "role": "system",
                "content": f"【历史摘要】\n{history_summary}",
            })

        # Block 3: Retrieved memories (if non-empty)
        retrieved_memories = blocks.get("retrieved_memories", "")
        if retrieved_memories and retrieved_memories.strip():
            messages.append({
                "role": "system",
                "content": f"【检索记忆】\n{retrieved_memories}",
            })

        # Block 4: Current user input
        messages.append({"role": "user", "content": user_text})

        logger.debug(
            "Assembled prompt: %d blocks, %d messages",
            sum(1 for v in blocks.values() if v and v.strip()),
            len(messages),
        )
        return messages
