"""
文件职责：交互管理器
处理与用户的直接交互逻辑，包括消息缓冲、输入节奏控制（防刷屏）、
错误消息反馈以及最终的消息发送调度。
"""

import threading
import time
import random
from typing import Callable, List, Dict, Optional
from src.core.config_loader import ConfigLoader
from src.core.chat_service import ChatService
from src.core.logger import get_logger

logger = get_logger("InteractionManager")

from src.core.session_controller import SessionController, AccessResult

class InteractionManager:
    def __init__(self, chat_service: ChatService, session_controller: SessionController):
        self._initialize(chat_service, session_controller)

    def _initialize(self, chat_service: ChatService, session_controller: SessionController):
        self.chat_service = chat_service
        self.session_controller = session_controller
        self.config_loader = ConfigLoader()
        self.system_config = self.config_loader.system_config
        
        # 缓冲状态
        self.user_message_buffer: Dict[int, List[str]] = {}
        self.user_timers: Dict[int, threading.Timer] = {}
        self.buffer_lock = threading.Lock()
        
        # 发送消息的回调函数 (user_id, text) -> None
        self.sender: Optional[Callable[[int, str], None]] = None
        
        # 播放动作的回调函数 (user_id, action_name) -> None
        self.action_player: Optional[Callable[[int, str], None]] = None

    def set_sender(self, sender_func: Callable[[int, str], None]):
        """
        设置发送消息的回调函数。
        sender_func 应该处理实际的 I/O (例如 Telegram send)。
        """
        self.sender = sender_func

    def set_action_player(self, player_func: Callable[[int, str], None]):
        """设置播放动作的回调函数"""
        self.action_player = player_func

    def add_user_message(self, user_id: int, message_text: str):
        """
        将用户消息添加到缓冲区并调度处理。
        包含权限检查。
        """
        access = self.session_controller.can_continue_session(user_id)
        
        if access == AccessResult.DENIED_PRIVATE:
            logger.info(f"[INTERACTION] IGNORE | user_id: {user_id} | reason: private_mode")
            # 可选：如果需要，可以在这里发送“系统繁忙”或“无权访问”的消息
            # 目前如果是硬拒绝，我们可能会回复一次
            if self.sender:
                self.sender(user_id, "🔒 机器人处于私有模式，您无权访问。")
            return
            
        if access == AccessResult.DENIED_INACTIVE:
            logger.info(f"[INTERACTION] IGNORE | user_id: {user_id} | reason: inactive")
            # 对于非活跃会话，静默忽略是标准行为（不回复随机消息）
            return

        with self.buffer_lock:
            if user_id not in self.user_message_buffer:
                self.user_message_buffer[user_id] = []
            
            self.user_message_buffer[user_id].append(message_text)
            current_size = len(self.user_message_buffer[user_id])
            logger.info(f"[BUFFER] ADD | user_id: {user_id} | current_size: {current_size}")
            
            # 重置计时器
            if user_id in self.user_timers:
                self.user_timers[user_id].cancel()
                logger.debug(f"[TIMER] RESET | user_id: {user_id}")
            
            # 从配置获取延迟
            try:
                min_time = self.system_config.message_buffer.collect_min_time
                max_time = self.system_config.message_buffer.collect_max_time
            except AttributeError:
                # 默认回退值
                min_time = 1.0
                max_time = 3.0
                
            collect_time = random.uniform(min_time, max_time)
            
            timer = threading.Timer(collect_time, self._process_buffer, args=[user_id])
            timer.daemon = True
            timer.start()
            self.user_timers[user_id] = timer
            logger.info(f"[TIMER] SCHEDULE | user_id: {user_id} | delay: {collect_time:.1f}s")

    def clear_user_state(self, user_id: int):
        """
        清理用户的缓冲和计时器（例如停止聊天时）。
        """
        with self.buffer_lock:
            if user_id in self.user_message_buffer:
                del self.user_message_buffer[user_id]
            if user_id in self.user_timers:
                self.user_timers[user_id].cancel()
                del self.user_timers[user_id]
            logger.info(f"[INTERACTION] CLEARED | user_id: {user_id}")

    def _process_buffer(self, user_id: int):
        """
        处理用户缓冲区中的消息。
        """
        with self.buffer_lock:
            # 从字典中移除计时器，因为它已经触发
            if user_id in self.user_timers:
                del self.user_timers[user_id]
            
            # 获取并清除消息
            messages = self.user_message_buffer.get(user_id, [])
            if not messages:
                return
            del self.user_message_buffer[user_id]
        
        # 合并消息
        full_text = "\n".join(messages)
        logger.info(f"[BUFFER] FLUSH | user_id: {user_id} | total_len: {len(full_text)}")
        
        try:
            # 调用 ChatService
            # 注意：response 可能是 str 或 AgentResponse 对象
            response = self.chat_service.process_user_input(user_id, full_text)
            
            # 处理复杂响应对象 (AgentResponse)
            text_to_send = response
            if hasattr(response, 'text'):
                text_to_send = response.text
                
                # 如果有动作且设置了播放器，则执行动作
                if hasattr(response, 'action') and response.action and self.action_player:
                    try:
                        self.action_player(user_id, response.action)
                    except Exception as ae:
                        logger.error(f"[INTERACTION] ACTION_FAIL | user_id: {user_id} | action: {response.action} | error: {ae}")

            # 分割并发送文本
            if text_to_send:
                self._send_response_chunks(user_id, text_to_send)
            
        except Exception as e:
            logger.error(f"[INTERACTION] ERROR | user_id: {user_id} | error: {e}", exc_info=True)
            if self.sender:
                # 友好的错误提示，不暴露内部异常
                self.sender(user_id, "⚠️ 抱歉，我现在有点晕，请稍后再试。")

    def _send_response_chunks(self, user_id: int, text: str):
        """
        通过 '$' 或换行符分割回复，并带延迟发送。
        """
        if not text:
            return

        # 分割逻辑：优先使用 '$'，然后是换行符
        # Prompt 通常指示使用 '$' 进行分割
        chunks = []
        if '$' in text:
            parts = text.split('$')
            for p in parts:
                if p.strip():
                    chunks.append(p.strip())
        else:
            # 如果没有 '$'，则回退到换行符分割
            lines = text.split('\n')
            for line in lines:
                if line.strip():
                    chunks.append(line.strip())
        
        if not chunks:
            chunks = [text]

        # 发送循环
        for i, chunk in enumerate(chunks):
            if self.sender:
                self.sender(user_id, chunk)
            
            # 块之间的延迟
            if i < len(chunks) - 1:
                # 简单的阅读时间计算：0.5s + 每个字符 0.05s，最长 3s
                # TODO: 优化节奏控制算法，使其更自然
                delay = min(3.0, 0.5 + len(chunk) * 0.05)
                time.sleep(delay)
