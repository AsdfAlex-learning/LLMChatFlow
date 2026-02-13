def comfort_reply_strategy(context: str) -> dict:
    """
    安慰/共情回复策略
    """
    return {
        "max_tokens": 200,
        "temperature": 0.8,
        "style_instruction": "Be gentle, supportive, and comforting."
    }
