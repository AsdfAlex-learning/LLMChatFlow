"""
文件职责：LLM 客户端
负责与 OpenAI 兼容的 API 进行通信（如 DeepSeek, ChatGPT）。
提供基础的对话补全功能，以及专门的工具函数（关键词提取、总结生成）。
"""

import requests
import time
from typing import List, Dict, Optional, Any
from src.core.config import SystemConfig
from src.core.logger import get_logger

logger = get_logger("LLMClient")

class LLMClient:
    def __init__(self, system_config: SystemConfig):
        self.config = system_config
        self.api_key = system_config.llm.api_key
        self.api_url = system_config.llm.api_url
        self.model = system_config.llm.model
        self.temperature = system_config.llm.temperature
        self.max_tokens = system_config.llm.max_tokens

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def chat_completion(self, messages: List[Dict[str, str]], temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> str:
        """
        调用 LLM 对话补全 API。
        """
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens
        }

        start_time = time.time()
        try:
            # TODO: 添加重试机制和流式输出支持
            response = requests.post(self.api_url, headers=self._get_headers(), json=data, timeout=60)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            
            duration = time.time() - start_time
            logger.info(f"[LLM] SUCCESS | model: {self.model} | duration: {duration:.2f}s | response_len: {len(content)}")
            
            return content
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[LLM] FAILED | model: {self.model} | duration: {duration:.2f}s | error: {str(e)}", exc_info=True)
            raise

    def extract_keywords(self, text: str) -> List[str]:
        """
        使用 LLM 从文本中提取关键词。
        """
        messages = [
            {"role": "system", "content": "提取输入文本的核心关键词，用逗号分隔，不超过5个词。"},
            {"role": "user", "content": text}
        ]
        try:
            content = self.chat_completion(messages, temperature=0.3, max_tokens=100)
            keywords = [k.strip() for k in content.split(',') if k.strip()]
            logger.debug(f"[LLM] EXTRACT_KEYWORDS | count: {len(keywords)} | keywords: {keywords}")
            return keywords
        except Exception as e:
            logger.warning(f"[LLM] EXTRACT_KEYWORDS_FAIL | error: {str(e)}")
            return text.split()[:5]

    def generate_user_summary(self, memories: List[str]) -> str:
        """
        根据记忆生成用户摘要。
        """
        if not memories:
            return "用户信息加载中..."
            
        messages = [
            {"role": "system", "content": "根据以下用户记忆，生成≤200字的USER_PROMPT，分核心层（永久属性）和动态层（临时事件）。核心层必加，动态层仅在相关时提及。"},
            {"role": "user", "content": "\n".join(memories)}
        ]
        try:
            summary = self.chat_completion(messages, temperature=0.5, max_tokens=500)
            logger.info(f"[LLM] GENERATE_SUMMARY | length: {len(summary)}")
            return summary
        except Exception as e:
            logger.error(f"[LLM] GENERATE_SUMMARY_FAIL | error: {str(e)}")
            return "用户信息加载中..."

    def extract_new_memories(self, conversation_text: str) -> List[tuple]:
        """
        从对话文本中提取新记忆。
        返回列表：(事件, 关键词, 重要度, 有效期)。
        """
        messages = [
            {
                "role": "system", "content": 
                    """从对话中提取用户的重要信息，按格式返回：
                        事件（YYYY-MM-DD + 具体事件）,关键词（逗号分隔）,重要度(0-100),有效期（天，365=永久）
                        仅保留重要信息，普通闲聊忽略。
                    """},
            {"role": "user", "content": conversation_text}
        ]
        
        try:
            content = self.chat_completion(messages, temperature=0.3, max_tokens=1000)
            memories = []
            for line in content.split('\n'):
                if line.strip():
                    parts = line.split(',')
                    if len(parts) >= 4:
                        # 简单的清理和验证
                        memories.append((parts[0].strip(), parts[1].strip(), int(parts[2].strip()), int(parts[3].strip())))
            
            logger.info(f"[LLM] EXTRACT_MEMORIES | count: {len(memories)}")
            return memories
        except Exception as e:
            logger.error(f"[LLM] EXTRACT_MEMORIES_FAIL | error: {str(e)}")
            return []
