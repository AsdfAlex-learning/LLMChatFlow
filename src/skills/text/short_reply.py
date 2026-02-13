def short_reply_strategy(context: str) -> dict:
    """
    短回复策略
    适用于：确认、简单的问候、或者不想多聊的时候
    """
    return {
        "max_tokens": 50,
        "temperature": 0.7,
        "style_instruction": "Keep it brief and concise."
    }
