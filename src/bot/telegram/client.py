import telebot
import requests
import time
from src.core.logger import get_logger
from src.core.config_loader import ConfigLoader

logger = get_logger("TelegramClient")

config_loader = ConfigLoader()
TELEGRAM_TOKEN = config_loader.system_config.telegram.bot_token

# 初始化全局 Bot 实例
tb_bot = telebot.TeleBot(TELEGRAM_TOKEN)

def safe_send_message(chat_id, text, max_attempts=3):
    """
    安全发送消息，包含重试机制
    """
    backoff = 1
    for attempt in range(max_attempts):
        try:
            tb_bot.send_message(chat_id, text)
            return True
        except requests.exceptions.RequestException as e:
            if attempt == max_attempts - 1:
                logger.error(f"[TELEGRAM] 发送失败 | chat_id: {chat_id} | error: {e}")
                return False
            time.sleep(backoff)
            backoff = min(backoff * 2, 10)
        except Exception as e:
            logger.error(f"[TELEGRAM] 发送错误 | chat_id: {chat_id} | error: {e}")
            return False
