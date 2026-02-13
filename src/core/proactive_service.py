"""
文件职责：主动消息服务 (Core)
负责主动消息的“决策”与“生成”。
实现 Policy (是否发送) 和 Agent (发送什么) 模式，不包含调度逻辑。
"""

from typing import Optional
import random
from src.core.session_controller import SessionController
from src.core.chat_service import ChatService
from src.core.llm_client import LLMClient
from src.core.config_loader import ConfigLoader
from src.core.prompt.prompt_builder import PromptBuilder
from src.core.logger import get_logger

logger = get_logger("ProactiveService")

class ProactiveService:
    """
    主动消息核心服务。
    职责:
    1. 策略 (Policy): 决定是否应该发起主动消息。
    2. 生成 (Generation): 生成主动消息的内容。
    """
    def __init__(self, session_controller: SessionController, chat_service: ChatService):
        self.session_controller = session_controller
        self.chat_service = chat_service
        self.config_loader = ConfigLoader()
        self.system_config = self.config_loader.system_config
        self.prompt_builder = PromptBuilder(self.config_loader)
        
        # 我们使用独立的 LLMClient 或复用现有的。
        # 由于 LLMClient 是轻量级的，我们可以新建一个。
        self.llm_client = LLMClient(self.system_config)
        
        # 策略配置 (目前硬编码，未来可移至 yaml)
        self.send_prob = 0.3

    def should_trigger(self, user_id: int) -> bool:
        """
        决定是否应该触发主动消息检查。
        检查会话状态和概率。
        """
        # 1. 检查会话是否活跃 (权限)
        # 我们需要访问 session_controller 状态。
        # session_controller.active_chats 是单一事实来源。
        if user_id not in self.session_controller.active_chats:
            logger.info(f"[POLICY] REJECT | user_id: {user_id} | reason: inactive_session")
            return False
        
        # 2. 随机概率检查
        if random.random() > self.send_prob:
            logger.info(f"[POLICY] REJECT | user_id: {user_id} | reason: probability_check_failed")
            return False
            
        logger.info(f"[POLICY] ACCEPT | user_id: {user_id}")
        return True

    def generate_content(self, user_id: int) -> Optional[str]:
        """
        生成主动消息的内容。
        这不会更新上下文历史 (发送时更新)。
        """
        try:
            logger.info(f"[AGENT] GEN_START | user_id: {user_id}")
            
            # 1. 从 ChatService 获取上下文摘要和记忆
            # 我们需要 ChatService 提供一个公共方法。
            # 假设我们使用了 `_get_user_prompt_summary` (虽然是受保护的，但在 Python 中可以访问，建议后续公开化)
            memory_text = self.chat_service._get_user_prompt_summary(user_id)
            
            # 2. 构建 Prompt
            # TODO: 将此 Prompt 模板移动到 prompt_manager 或配置文件中，避免硬编码
            instruction = (
                "（系统指令：请忽略上文的‘回复用户’要求。现在是空闲时间，请根据【用户记忆】主动发起一个温馨的话题。"
                "语气自然亲切，不要太生硬，一两句话即可。）"
            )
            
            # 使用 PromptBuilder 构建 Prompt
            final_prompt = self.prompt_builder.build(
                user_input=instruction, # 这里将指令作为 user_input 传入，因为主要是触发生成
                memory_str=memory_text,
                context_str="暂无" 
            )
            
            # 3. 调用 LLM
            response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": final_prompt}]
            )
            
            content = response.strip()
            logger.info(f"[AGENT] GEN_SUCCESS | user_id: {user_id} | len: {len(content)}")
            return content
            
        except Exception as e:
            logger.error(f"[AGENT] GEN_FAIL | user_id: {user_id} | error: {e}", exc_info=True)
            return None
