class TelegramRenderer:
    """
    Telegram 专用渲染逻辑
    例如：Markdown 转义、消息分片、特殊格式处理
    """
    
    @staticmethod
    def render_text(text: str) -> str:
        # 简单的占位，未来可以处理 MarkdownV2 的转义
        return text
        
    @staticmethod
    def split_long_message(text: str, limit: int = 4096) -> list[str]:
        """
        切分过长的 Telegram 消息
        """
        return [text[i:i+limit] for i in range(0, len(text), limit)]
