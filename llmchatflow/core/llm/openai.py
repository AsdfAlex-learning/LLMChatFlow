from typing import List, Dict, Optional, Any
import os
from openai import OpenAI, AsyncOpenAI
from .base import LLMClient

class OpenAIClient(LLMClient):
    """OpenAI (and compatible) LLM Client implementation."""

    def __init__(
        self, 
        api_key: Optional[str] = None, 
        base_url: Optional[str] = None, 
        model: str = "gpt-3.5-turbo",
        default_temperature: float = 0.7,
        default_max_tokens: int = 1000
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model = model
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.aclient = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        temperature: Optional[float] = None, 
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature if temperature is not None else self.default_temperature,
            max_tokens=max_tokens if max_tokens is not None else self.default_max_tokens,
            **kwargs
        )
        return response.choices[0].message.content

    async def achat_completion(
        self, 
        messages: List[Dict[str, str]], 
        temperature: Optional[float] = None, 
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        response = await self.aclient.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature if temperature is not None else self.default_temperature,
            max_tokens=max_tokens if max_tokens is not None else self.default_max_tokens,
            **kwargs
        )
        return response.choices[0].message.content
