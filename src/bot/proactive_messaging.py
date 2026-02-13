import threading
import time
import random
from typing import Callable, Dict, Optional
from src.core.proactive_service import ProactiveService
from src.core.chat_service import ChatService
from src.core.logger import get_logger
from src.core.config_loader import ConfigLoader

logger = get_logger("ProactiveScheduler")

class ProactiveScheduler:
    """
    主动消息调度器。
    职责:
    1. 计时 (决定何时检查)。
    2. 调度 (决定延迟时间)。
    3. 执行 (通过 I/O 回调发送消息)。
    
    将“内容决策”委托给 ProactiveService。
    """
    def __init__(self, 
                 proactive_service: ProactiveService, 
                 chat_service: ChatService,
                 sender: Callable[[int, str], None]):
        self.proactive_service = proactive_service
        self.chat_service = chat_service
        self.sender = sender
        
        self.check_timers: Dict[int, threading.Timer] = {}
        self.send_timers: Dict[int, threading.Timer] = {}
        self.lock = threading.Lock()
        
        # 配置加载
        self.config_loader = ConfigLoader()
        self.system_config = self.config_loader.system_config
        
        # 配置 (时间间隔)
        self.check_interval_min = self.system_config.proactive.check_interval_min
        self.check_interval_max = self.system_config.proactive.check_interval_max
        self.send_delay_min = self.system_config.proactive.send_delay_min
        self.send_delay_max = self.system_config.proactive.send_delay_max

    def start(self, user_id: int):
        """为用户启动调度器。"""
        logger.info(f"[SCHEDULER] START | user_id: {user_id}")
        self.on_user_activity(user_id)

    def stop(self, user_id: int):
        """停止用户的调度器。"""
        with self.lock:
            if user_id in self.check_timers:
                self.check_timers[user_id].cancel()
                del self.check_timers[user_id]
            if user_id in self.send_timers:
                self.send_timers[user_id].cancel()
                del self.send_timers[user_id]
        logger.info(f"[SCHEDULER] STOP | user_id: {user_id}")

    def on_user_activity(self, user_id: int):
        """
        当用户活跃时调用。
        重置检查计时器并取消任何挂起的主动发送。
        """
        with self.lock:
            # 取消挂起的发送 (不要打断用户)
            if user_id in self.send_timers:
                logger.info(f"[SCHEDULER] CANCEL_SEND | user_id: {user_id} | reason: user_active")
                self.send_timers[user_id].cancel()
                del self.send_timers[user_id]
            
            # 取消现有的检查计时器
            if user_id in self.check_timers:
                self.check_timers[user_id].cancel()
            
            # 调度下一次检查
            delay = random.uniform(self.check_interval_min, self.check_interval_max)
            timer = threading.Timer(delay, self._check_callback, args=[user_id])
            timer.daemon = True
            timer.start()
            self.check_timers[user_id] = timer
            logger.info(f"[SCHEDULER] RESET | user_id: {user_id} | next_check_in: {delay:.1f}s")

    def _check_callback(self, user_id: int):
        """检查计时器的回调。"""
        with self.lock:
            if user_id in self.check_timers:
                del self.check_timers[user_id]

        logger.debug(f"[SCHEDULER] TRIGGER_CHECK | user_id: {user_id}")

        # 1. 询问 Core: 我们应该触发吗？
        if not self.proactive_service.should_trigger(user_id):
            self.on_user_activity(user_id) # 重新调度下一次检查
            return

        # 2. 询问 Core: 生成内容
        content = self.proactive_service.generate_content(user_id)
        if not content:
            self.on_user_activity(user_id)
            return

        # 3. 调度发送
        delay = random.uniform(self.send_delay_min, self.send_delay_max)
        logger.info(f"[SCHEDULER] SCHEDULE_SEND | user_id: {user_id} | delay: {delay:.1f}s | content_len: {len(content)}")
        
        timer = threading.Timer(delay, self._execute_send, args=[user_id, content])
        timer.daemon = True
        timer.start()
        
        with self.lock:
            self.send_timers[user_id] = timer

    def _execute_send(self, user_id: int, content: str):
        """Execute the actual send."""
        with self.lock:
            if user_id in self.send_timers:
                del self.send_timers[user_id]
        
        try:
            logger.info(f"[SCHEDULER] SEND | user_id: {user_id} | content_len: {len(content)}")
            
            # Use the injected sender (e.g., Telegram sender)
            if self.sender:
                self.sender(user_id, content)
                
                # Update Context (Core State)
                self.chat_service.add_assistant_message_to_context(user_id, content)
            else:
                logger.error("[SCHEDULER] SEND_FAIL | user_id: {user_id} | error: No sender configured")
                
        except Exception as e:
            logger.error(f"[SCHEDULER] SEND_FAIL | user_id: {user_id} | error: {e}", exc_info=True)
        
        # Reset loop
        self.on_user_activity(user_id)
