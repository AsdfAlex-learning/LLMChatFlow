import time
import logging
from typing import List, Dict, Optional, Any
import os
import requests
import asyncio
from .base import LLMClient

logger = logging.getLogger(__name__)


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
        max_retries: int = 3,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "").rstrip("/")
        self.model = model
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
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

        Retries on transient failures (connection errors, 5xx) with exponential backoff.

        Args:
            messages: List of {'role': str, 'content': str} message dicts.
            temperature: Sampling temperature (falls back to default).
            max_tokens: Max tokens to generate (falls back to default).

        Returns:
            The assistant's reply text.

        Raises:
            requests.HTTPError: For non-retryable HTTP errors (4xx) or after exhausting retries.
            requests.ConnectionError: For connection failures after exhausting retries.
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

        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = requests.post(
                    self._endpoint, headers=self._headers(), json=payload, timeout=self.timeout
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except (requests.ConnectionError, requests.Timeout) as e:
                last_exc = e
                wait = 2 ** attempt  # 1, 2, 4 seconds
                logger.warning(
                    "LLM connection failed (attempt %d/%d), retrying in %ds",
                    attempt + 1, self.max_retries, wait,
                )
                if attempt < self.max_retries - 1:
                    time.sleep(wait)
            except requests.HTTPError as e:
                last_exc = e
                status = resp.status_code
                if status >= 500 and attempt < self.max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        "LLM server error %d (attempt %d/%d), retrying in %ds",
                        status, attempt + 1, self.max_retries, wait,
                    )
                    time.sleep(wait)
                else:
                    # Non-retryable (4xx) or retries exhausted — raise without exposing API key
                    raise requests.HTTPError(
                        f"LLM API returned HTTP {status}", response=resp
                    ) from e
        raise last_exc  # type: ignore[misc]

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
