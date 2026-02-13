"""
文件职责：聊天服务
核心业务逻辑层，负责协调 LLM 调用、上下文管理和记忆更新。
作为 Core 的主要入口点，处理用户输入并返回 AI 响应。
"""

import threading
import time
from typing import Dict, Tuple, Set, Optional, List, Any

from src.core.config_loader import ConfigLoader
from src.core.context import ConversationContext
from src.core.llm_client import LLMClient
from src.core.memory.service import MemoryService
from src.core.session_controller import SessionController
from src.core.logger import get_logger

# Agent Architecture
from src.agent.orchestrator import ExpressionOrchestrator, AgentResponse
from src.agent.state import PersonaState, RelationshipStage

logger = get_logger("ChatService")

class ChatService:
    def __init__(self, session_controller: SessionController, orchestrator: ExpressionOrchestrator):
        self._initialize(session_controller, orchestrator)

    def _initialize(self, session_controller: SessionController, orchestrator: ExpressionOrchestrator):
        self.config_loader = ConfigLoader()
        self.system_config = self.config_loader.system_config
        
        self.llm_client = LLMClient(self.system_config)
        self.session_controller = session_controller
        self.orchestrator = orchestrator
        
        # 状态管理
        self.chat_contexts: Dict[int, ConversationContext] = {}
        self.user_memories: Dict[int, MemoryService] = {}
        self.user_states: Dict[int, PersonaState] = {} # 新增: 用户人格状态
        self.user_prompt_cache: Dict[int, Tuple[str, float]] = {}
        self.user_message_counts: Dict[int, int] = {}
        
        # 锁
        self.context_lock = threading.Lock()  # 用于 chat_contexts
        self.memory_lock = threading.Lock()   # 用于 user_memories
        self.state_lock = threading.Lock()    # 用于其他状态 (counts, cache)

    def start_chat(self, user_id: int):
        """开启聊天会话，初始化资源。"""
        self.get_context(user_id)
        self.get_user_memory(user_id)
        logger.info(f"[CHAT] START | user_id: {user_id}")

    def stop_chat(self, user_id: int):
        """停止聊天并清理资源。"""
        self.clean_resources(user_id)
        logger.info(f"[CHAT] STOP | user_id: {user_id}")

    def clean_resources(self, user_id: int):
        """清理用户资源（会话停止时调用）。"""
        with self.state_lock:
            if user_id in self.user_message_counts:
                del self.user_message_counts[user_id]
            if user_id in self.user_prompt_cache:
                del self.user_prompt_cache[user_id]
            if user_id in self.user_states:
                del self.user_states[user_id]
        
        with self.context_lock:
            if user_id in self.chat_contexts:
                del self.chat_contexts[user_id]
        
        logger.debug(f"[RESOURCE] CLEAN | user_id: {user_id}")

    def get_context(self, user_id: int) -> ConversationContext:
        """获取或创建用户的对话上下文。"""
        with self.context_lock:
            if user_id not in self.chat_contexts:
                self.chat_contexts[user_id] = ConversationContext()
            return self.chat_contexts[user_id]

    def get_user_state(self, user_id: int) -> PersonaState:
        """获取或创建用户的 PersonaState"""
        with self.state_lock:
            if user_id not in self.user_states:
                # 默认状态
                self.user_states[user_id] = PersonaState()
                # 简单逻辑：如果是 Owner，直接设为 PARTNER
                if user_id == self.session_controller.owner_id:
                     self.user_states[user_id].relationship_stage = RelationshipStage.PARTNER
            return self.user_states[user_id]

    def get_user_memory(self, user_id: int) -> MemoryService:
        """获取或创建用户的长期记忆实例。"""
        with self.memory_lock:
            if user_id not in self.user_memories:
                self.user_memories[user_id] = MemoryService(user_id)
            return self.user_memories[user_id]

    def add_user_message_to_context(self, user_id: int, message: str):
        """将用户消息添加到上下文，但不触发回复。"""
        ctx = self.get_context(user_id)
        ctx.add_message("user", message)
        logger.debug(f"[CONTEXT] ADD_USER | user_id: {user_id} | len: {len(message)}")

    def add_assistant_message_to_context(self, user_id: int, message: str):
        """将助手消息添加到上下文。"""
        ctx = self.get_context(user_id)
        ctx.add_message("assistant", message)
        logger.debug(f"[CONTEXT] ADD_BOT | user_id: {user_id} | len: {len(message)}")

    def process_user_input(self, user_id: int, user_input: str) -> Any:
        """
        处理用户输入：
        1. 添加到上下文
        2. 准备上下文和记忆字符串
        3. 调用 Orchestrator 获取响应 (AgentResponse)
        4. 添加回复到上下文
        5. 触发记忆提取
        6. 返回响应对象 (AgentResponse)
        """
        # 1. 添加到上下文
        self.add_user_message_to_context(user_id, user_input)
        
        # 2. 准备上下文和记忆
        ctx = self.get_context(user_id)
        conversation_str = ctx.format(exclude_last_n=1)
        user_summary = self._get_user_prompt_summary(user_id)
        
        # 获取用户状态
        state = self.get_user_state(user_id)
        
        # 记录上下文状态
        logger.info(f"[CHAT] PROCESS | user_id: {user_id} | context_turns: {len(ctx.history)} | state: {state.relationship_stage.name}")
        
        # 3. 调用 Orchestrator
        try:
            start_time = time.time()
            
            # 使用新架构进行编排
            response = self.orchestrator.orchestrate_response(
                user_input=user_input,
                state=state,
                context_str=conversation_str,
                memory_str=user_summary
            )
            
            duration = time.time() - start_time
            
            if response:
                logger.info(f"[ORCHESTRATOR] SUCCESS | user_id: {user_id} | duration: {duration:.2f}s | action: {response.action}")
                # 4. 添加回复到上下文
                self.add_assistant_message_to_context(user_id, response.text)
                
                # 5. 更新记忆
                self._update_memories(user_id, user_input, response.text)
                
                return response
            else:
                logger.info(f"[ORCHESTRATOR] SILENCE | user_id: {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] FAILED | user_id: {user_id} | error: {e}", exc_info=True)
            raise e

    def _get_user_prompt_summary(self, user_id: int) -> str:
        """
        获取用于 Prompt 的记忆摘要。
        如果缓存有效则使用缓存。
        """
        with self.state_lock:
            cache = self.user_prompt_cache.get(user_id)
            if cache:
                content, timestamp = cache
                # TODO: 实现更智能的缓存失效逻辑（例如基于时间或更新事件）
                # 目前只是简单返回
                pass 

        # 加载记忆
        memory_service = self.get_user_memory(user_id)
        valid_memories = memory_service.get_relevant_memories()
        
        if not valid_memories:
            return "暂无特殊记忆"
            
        # 按重要性排序 (索引 3)
        sorted_memories = sorted(valid_memories, key=lambda x: x[3], reverse=True)
        top_memories = sorted_memories[:20] # 限制前 20 条
        
        mem_text = "\n".join([f"- {m[1]} (关键词:{m[2]})" for m in top_memories])
        return mem_text

    def _update_memories(self, user_id: int, user_input: str, response: str):
        """
        基于交互更新长期记忆。
        简单逻辑：计数消息，每 N 条触发一次提取。
        """
        with self.state_lock:
            count = self.user_message_counts.get(user_id, 0) + 1
            self.user_message_counts[user_id] = count
            
        # 每 5 条消息提取一次
        if count % 5 == 0:
            logger.info(f"[MEMORY] TRIGGER_EXTRACT | user_id: {user_id} | msg_count: {count}")
            # TODO: 实现真正的记忆提取逻辑
            # 这里应该调用 LLM 来提取事实，并使用 MemoryManager 存储
            # 建议使用异步任务来避免阻塞聊天
            pass
