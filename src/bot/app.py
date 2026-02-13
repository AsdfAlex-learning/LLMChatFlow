from src.core.logger import get_logger
from src.core.session_controller import SessionController
from src.core.chat_service import ChatService
from src.core.interaction import InteractionManager
from src.bot.proactive_messaging import ProactiveScheduler
from src.llm_system.local_api_caller import call_local_llm

logger = get_logger("BotApplication")

class BotApplication:
    """
    Bot 业务编排层
    负责协调各个服务，但不直接处理 Telegram 消息对象
    """
    def __init__(self, 
                 session_controller: SessionController,
                 chat_service: ChatService,
                 interaction_manager: InteractionManager,
                 proactive_scheduler: ProactiveScheduler):
        self.session_controller = session_controller
        self.chat_service = chat_service
        self.interaction_manager = interaction_manager
        self.proactive_scheduler = proactive_scheduler

    def get_help_text(self) -> str:
        return (
            "📖 可用命令：\n"
            "/start_aiGF - 开启ai女友对话模式\n"
            "/stop_aiGF - 关闭ai女友对话模式\n"
            "/help - 显示此帮助信息"
        )

    def start_ai_session(self, user_id: int) -> str:
        if not self.session_controller.start_session(user_id):
            return "🔒 机器人当前处于私有模式，仅管理员可用。"
        
        self.chat_service.start_chat(user_id)
        self.proactive_scheduler.start(user_id)
        
        logger.info(f"[APP] 会话开启 | user_id: {user_id}")
        return "✅ ai女友对话已开启！现在可以直接发送消息获取回复，输入/stop_aiGF关闭该模式。"

    def stop_ai_session(self, user_id: int) -> str:
        self.chat_service.stop_chat(user_id)
        self.session_controller.stop_session(user_id)
        self.interaction_manager.clear_user_state(user_id)
        self.proactive_scheduler.stop(user_id)
        
        logger.info(f"[APP] 会话结束 | user_id: {user_id}")
        return "❌ ai女友对话模式已关闭！"

    def handle_user_message(self, user_id: int, user_input: str) -> str:
        if not user_input:
            return "⚠️ 消息内容不能为空，请重新输入！"

        # 检查是否开启本地 API 模式
        llm_config = self.chat_service.system_config.llm
        if llm_config.use_local_api:
            logger.info(f"[APP] Local API Mode | user_id: {user_id}")
            return call_local_llm(
                message=user_input,
                api_url=llm_config.local_api_url,
                model="local-model", # 或者使用 llm_config.model
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens
            )

        # 重置主动消息计时器
        self.proactive_scheduler.on_user_activity(user_id)

        # 异步处理消息
        self.interaction_manager.add_user_message(user_id, user_input)
        return None  # 无同步回复
