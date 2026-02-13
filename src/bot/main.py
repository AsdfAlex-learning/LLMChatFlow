import time
from src.core.logger import get_logger

# 引入显式的创建函数，而不是隐式的全局变量
from src.bot.wiring import create_bot_context
from src.bot.telegram.handlers import register_handlers
from src.bot.telegram.polling import start_polling_thread

logger = get_logger("Main")

def main():
    logger.info("🚀 正在初始化 Telegram Chatbot...")
    
    # 1. 创建核心对象（bot / agent / memory）
    # 创建所有的 Service、Controller，并组装在一起
    logger.info("1️⃣ 创建 Bot Context")
    context = create_bot_context()
    
    # 2. 注册 Telegram handlers
    logger.info("2️⃣ 注册 Telegram Handlers")
    register_handlers(context.bot, context.app)
    
    # 3. 启动轮询线程
    logger.info("3️⃣ 启动 Telegram Polling")
    start_polling_thread(context.bot)
    
    logger.info("✅ 机器人已启动！(按 Ctrl+C 停止)")
    
    # 主线程阻塞，保持程序运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 正在停止机器人...")
    except Exception as e:
        logger.error(f"❌ 运行时发生错误: {e}")
        raise

if __name__ == "__main__":
    main()
