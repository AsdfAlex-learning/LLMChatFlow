def long_emotional_reply_strategy(context: str) -> dict:
    """
    长情感情感回复策略
    适用于：深度交流、安慰、讲故事
    """
    return {
        "max_tokens": 300,
        "temperature": 0.9,
        "style_instruction": "Be expressive, emotional, and detailed."
    }
