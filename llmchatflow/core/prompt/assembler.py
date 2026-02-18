from typing import List, Dict
from .base import PromptTemplate


class SimplePromptAssembler(PromptTemplate):
    def __init__(self, system_prompt: str = "你是一个有同理心且高效的助手。"):
        self.system_prompt = system_prompt

    def assemble(self, history_text: str, user_text: str) -> List[Dict[str, str]]:
        prompt = f"【历史记忆】\n{history_text}\n【当前提问】\n{user_text}"
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
