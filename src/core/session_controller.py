"""
文件职责：会话控制器
负责管理全局会话状态、权限控制和并发锁。
作为 Single Source of Truth，决定谁可以开始会话，谁处于活跃状态。
"""

import threading
from typing import Set
from enum import Enum, auto
from src.core.logger import get_logger

logger = get_logger("SessionController")

class AccessResult(Enum):
    ALLOWED = auto()
    DENIED_PRIVATE = auto()
    DENIED_INACTIVE = auto()

class SessionController:
    def __init__(self, owner_id: int, private_mode_default: bool):
        self.owner_id = owner_id
        self.private_mode_enabled = private_mode_default
        self.active_chats: Set[int] = set()
        self.lock = threading.Lock()
        logger.info(f"初始化完成 | Owner ID: {self.owner_id} | 私有模式: {self.private_mode_enabled}")

    def can_start_session(self, user_id: int) -> bool:
        if self.private_mode_enabled and user_id != self.owner_id:
            logger.warning(f"[SESSION] DENIED | user_id: {user_id} | reason: private_mode_check")
            return False
        return True

    def can_continue_session(self, user_id: int) -> AccessResult:
        if self.private_mode_enabled and user_id != self.owner_id:
            logger.warning(f"[SESSION] DENIED | user_id: {user_id} | reason: private_mode_enforced")
            return AccessResult.DENIED_PRIVATE
        if user_id not in self.active_chats:
            # 这是一个常见情况（用户发消息但没 /start），级别设为 DEBUG 或 INFO
            logger.info(f"[SESSION] DENIED | user_id: {user_id} | reason: inactive")
            return AccessResult.DENIED_INACTIVE
        return AccessResult.ALLOWED

    def start_session(self, user_id: int) -> bool:
        """
        尝试为用户启动会话。
        成功返回 True，权限拒绝返回 False。
        """
        if not self.can_start_session(user_id):
            logger.warning(f"[SESSION] FAIL_START | user_id: {user_id} | reason: private_mode")
            return False
            
        with self.lock:
            self.active_chats.add(user_id)
            logger.info(f"[SESSION] START | user_id: {user_id}")
            return True

    def stop_session(self, user_id: int):
        """停止用户的会话。"""
        with self.lock:
            if user_id in self.active_chats:
                self.active_chats.discard(user_id)
                logger.info(f"[SESSION] STOP | user_id: {user_id} | reason: manual")
            else:
                logger.debug(f"[SESSION] STOP_IGNORE | user_id: {user_id} | reason: already_stopped")

    def is_session_active(self, user_id: int) -> bool:
        """检查用户是否有活跃会话。"""
        with self.lock:
            return user_id in self.active_chats
