"""
文件职责：统一日志系统
提供标准化的日志记录器，支持文件轮转和控制台输出。
格式化日志以匹配 DEBUG_LIST.md 中的观测建议。
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

# 确保 logs 目录存在
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 全局日志配置
LOG_FILE = os.path.join(LOG_DIR, "bot.log")
MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_is_configured = False

def configure_logging(level: int = logging.INFO):
    """
    配置全局日志系统。
    应在程序启动时调用一次。
    """
    global _is_configured
    if _is_configured:
        return

    # 获取根记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除现有的处理器（防止重复）
    if root_logger.handlers:
        root_logger.handlers.clear()

    # 1. 文件处理器 (Rotating)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    file_handler.setLevel(level)
    root_logger.addHandler(file_handler)

    # 2. 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)

    # 抑制一些嘈杂的第三方库日志
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telebot").setLevel(logging.INFO)

    _is_configured = True
    logging.info(f"日志系统已初始化。日志文件路径: {LOG_FILE}")

def get_logger(name: str) -> logging.Logger:
    """
    获取一个带命名的记录器。
    
    Args:
        name (str): 模块名称，建议使用 __name__ 或自定义服务名 (e.g. "SessionController")
    
    Returns:
        logging.Logger: 配置好的记录器实例
    """
    if not _is_configured:
        # 如果尚未配置，则使用默认配置（防止导入顺序导致的未初始化问题）
        configure_logging()
        
    return logging.getLogger(name)
