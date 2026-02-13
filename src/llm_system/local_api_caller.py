import requests
import json
from typing import Optional, Dict, Any

def call_local_llm(
    message: str, 
    api_url: str = "http://localhost:8000/v1/chat/completions",
    model: str = "local-model",
    temperature: float = 0.7,
    max_tokens: int = 1024
) -> str:
    """
    调用本地 LLM API (OpenAI 兼容接口)
    
    Args:
        message: 用户发送的消息内容
        api_url: 本地 API 地址
        model: 模型名称
        temperature: 采样温度
        max_tokens: 最大回复长度
        
    Returns:
        str: LLM 的回复内容
    """
    headers = {
        "Content-Type": "application/json"
    }
    
    # 构造 messages 列表
    messages = [
        {"role": "user", "content": message}
    ]
    
    data = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }
    
    try:
        print(f"[LocalAPI] Sending request to {api_url}...")
        response = requests.post(api_url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        return content
        
    except requests.exceptions.ConnectionError:
        return "❌ 无法连接到本地 API，请确认服务已在 localhost:8000 启动。"
    except Exception as e:
        return f"❌ Local API 调用失败: {str(e)}"
