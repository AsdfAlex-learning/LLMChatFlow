import os
from dataclasses import dataclass
import telebot

from src.core.config_loader import ConfigLoader
from src.core.prompt.prompt_builder import PromptBuilder
from src.core.session_controller import SessionController
from src.core.chat_service import ChatService
from src.core.interaction import InteractionManager
from src.core.proactive_service import ProactiveService
from src.core.llm_client import LLMClient
from src.bot.proactive_messaging import ProactiveScheduler
from src.core.logger import get_logger
from src.bot.app import BotApplication

# Agent Components
from src.agent.empathy_planner import EmpathyPlanner
from src.agent.orchestrator import ExpressionOrchestrator

logger = get_logger("Wiring")

@dataclass
class BotContext:
    bot: telebot.TeleBot
    app: BotApplication
    config: ConfigLoader

def create_bot_context() -> BotContext:
    """
    显示创建并组装所有核心对象
    """
    logger.info("🔧 正在组装 Bot 上下文...")
    
    # 1. 加载配置
    config_loader = ConfigLoader()
    system_config = config_loader.system_config
    
    # 2. 初始化 Telegram Bot 客户端
    # 注意：这里我们不再依赖 client.py 中的全局变量，而是每次创建新的
    bot = telebot.TeleBot(system_config.telegram.bot_token)
    
    # 定义发送函数适配器
    def telegram_sender(uid, txt):
        try:
            bot.send_message(uid, txt)
            return True
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False

    # 3. 初始化核心服务
    session_controller = SessionController(
        owner_id=system_config.telegram.owner_id,
        private_mode_default=system_config.bot.private_mode_default
    )
    
    # Agent 组件初始化
    llm_client = LLMClient(system_config)
    empathy_planner = EmpathyPlanner()
    prompt_builder = PromptBuilder(config_loader)
    orchestrator = ExpressionOrchestrator(empathy_planner, llm_client, prompt_builder)
    
    chat_service = ChatService(session_controller, orchestrator)
    proactive_service = ProactiveService(session_controller, chat_service)
    
    # 4. 初始化交互与主动消息
    interaction_manager = InteractionManager(chat_service, session_controller)
    interaction_manager.set_sender(telegram_sender)
    
    # 动作播放适配器
    def telegram_action_player(uid, action):
        # 简单实现：将动作转换为斜体文字发送
        # 实际项目中可能需要更复杂的表现（如表情包、贴纸等）
        try:
            bot.send_message(uid, f"_{action}_", parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"动作播放失败: {e}")

    interaction_manager.set_action_player(telegram_action_player)
    
    proactive_scheduler = ProactiveScheduler(
        proactive_service=proactive_service,
        chat_service=chat_service,
        sender=telegram_sender
    )
    
    # 5. 初始化应用外观
    bot_app = BotApplication(
        session_controller=session_controller,
        chat_service=chat_service,
        interaction_manager=interaction_manager,
        proactive_scheduler=proactive_scheduler
    )
    
    logger.info("✅ Bot 上下文组装完成")
    
    return BotContext(
        bot=bot,
        app=bot_app,
        config=config_loader
    )
