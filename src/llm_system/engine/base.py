from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Generator

class BaseEngine(ABC):
    """
    LLM 推理引擎的抽象基类。
    所有具体的推理实现（如 HuggingFace, vLLM 等）都应继承此类。
    """

    @abstractmethod
    def load_model(self, model_path: str, **kwargs) -> None:
        """
        从指定路径加载模型。
        """
        pass

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        基于给定的提示词生成文本。
        """
        pass

    @abstractmethod
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        基于消息列表生成对话补全响应。
        期望的返回格式应部分或完全匹配 OpenAI API 的响应结构。
        """
        pass
    
    @abstractmethod
    def stream_chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        """
        流式生成对话补全块（Chunks）。
        """
        pass
