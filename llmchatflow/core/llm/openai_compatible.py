from typing import List, Dict, Optional, Any
import os
import requests
import asyncio
from .base import LLMClient


class OpenAICompatibleClient(LLMClient):
    """OpenAI-compatible client implemented via HTTP requests."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        default_temperature: float = 0.7,
        default_max_tokens: int = 1000,
        timeout: int = 60,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "").rstrip("/")
        self.model = model
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self.timeout = timeout
        self._endpoint = (
            f"{self.base_url}/chat/completions"
            if self.base_url
            else "https://api.openai.com/v1/chat/completions"
        )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Send a synchronous chat completion request to the OpenAI-compatible API.

        Args:
            messages: List of {'role': str, 'content': str} message dicts.
            temperature: Sampling temperature (falls back to default).
            max_tokens: Max tokens to generate (falls back to default).

        Returns:
            The assistant's reply text.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": (
                temperature if temperature is not None else self.default_temperature
            ),
            "max_tokens": (
                max_tokens if max_tokens is not None else self.default_max_tokens
            ),
        }
        payload.update(kwargs or {})
        resp = requests.post(
            self._endpoint, headers=self._headers(), json=payload, timeout=self.timeout
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def achat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Async wrapper that delegates to chat_completion via thread executor.

        See chat_completion for parameter docs.
        """
        # Simple async wrapper using thread executor
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.chat_completion(
                messages, temperature=temperature, max_tokens=max_tokens, **kwargs
            ),
        )
