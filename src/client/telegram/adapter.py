import telebot
from src.client.base import BaseClient
from src.core.logger import get_logger

logger = get_logger("TelegramAdapter")

class TelegramAdapter(BaseClient):
    """
    Telegram 平台适配器
    实现具体的发送逻辑
    """
    
    def __init__(self, bot: telebot.TeleBot):
        self.bot = bot

    async def send_text(self, target_id: str, text: str):
        try:
            # 这里的 target_id 通常是 chat_id
            self.bot.send_message(target_id, text)
            logger.info(f"[Telegram] 发送文本到 {target_id}: {text[:20]}...")
        except Exception as e:
            logger.error(f"[Telegram] 发送文本失败: {e}")

    async def play_action(self, target_id: str, action_name: str):
        """
        在 Telegram 中，动作通常表现为 Chat Action (typing...) 
        或者特定的 Sticker
        """
        try:
            # 示例：发送 typing 状态来模拟"正在做动作"
            # 实际项目中可能映射到具体的 Sticker ID
            self.bot.send_chat_action(target_id, 'typing')
            logger.info(f"[Telegram] 执行动作 {action_name} 到 {target_id}")
        except Exception as e:
            logger.error(f"[Telegram] 执行动作失败: {e}")

    async def play_voice(self, target_id: str, audio_data: bytes):
        try:
            self.bot.send_voice(target_id, audio_data)
        except Exception as e:
            logger.error(f"[Telegram] 播放语音失败: {e}")
