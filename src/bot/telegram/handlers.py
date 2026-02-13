import telebot
from src.bot.app import BotApplication
from src.core.logger import get_logger

logger = get_logger("TelegramHandlers")

def register_handlers(bot: telebot.TeleBot, app: BotApplication):
    """
    显式注册 Telegram 消息处理器
    """
    logger.info("📝 正在注册消息处理器...")

    @bot.message_handler(func=lambda msg: msg.text.strip() == "/help")
    def handle_help(message):
        logger.info(f"[TELEGRAM] 收到帮助请求 | user_id: {message.from_user.id}")
        response = app.get_help_text()
        bot.reply_to(message, response)

    @bot.message_handler(func=lambda msg: msg.text.strip() == "/start_aiGF")
    def handle_start_ai_chat(message):
        user_id = message.from_user.id
        response = app.start_ai_session(user_id)
        bot.reply_to(message, response)

    @bot.message_handler(func=lambda msg: msg.text.strip() == "/stop_aiGF")
    def handle_stop_ai_chat(message):
        user_id = message.from_user.id
        response = app.stop_ai_session(user_id)
        bot.reply_to(message, response)

    @bot.message_handler(func=lambda msg: True)
    def handle_ai_chat(message):
        # 过滤命令
        if message.text.strip().startswith(('/start_aiGF', '/stop_aiGF', '/help')):
            return
        
        user_id = message.from_user.id
        user_input = message.text.strip()
        
        # 调用 App 处理
        response = app.handle_user_message(user_id, user_input)
        
        if response:
            bot.reply_to(message, response)
            
    logger.info("✅ 消息处理器注册完成")
