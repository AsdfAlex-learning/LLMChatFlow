"""
文件职责：API 注册表
负责动态发现、加载和管理所有外部 API 服务（如天气、搜索等）。
实现了自动发现机制，确保新添加的 API 模块能被系统识别。
"""

import importlib
import os
import inspect
import logging
from src.core.config_loader import ConfigLoader
from src.api.base.base_api import BaseAPI

class APIRegistry:
    _instance = None
    _apis = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(APIRegistry, cls).__new__(cls)
            cls._instance._discover_and_register()
        return cls._instance

    def _discover_and_register(self):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        api_dir = os.path.join(project_root, "src", "api")
        config_loader = ConfigLoader()

        # 遍历 src/api 下的子目录
        for item in os.listdir(api_dir):
            item_path = os.path.join(api_dir, item)
            if os.path.isdir(item_path) and item != "__pycache__" and item != "base":
                # 尝试导入模块
                try:
                    # 假设模块名为 [item]_api.py，例如 weather_api.py
                    module_name = f"src.api.{item}.{item}_api"
                    module = importlib.import_module(module_name)
                    
                    # 查找实现了 BaseAPI 的类
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and issubclass(obj, BaseAPI) and obj is not BaseAPI:
                            # 读取配置
                            api_config = config_loader.get_config(item)
                            if api_config.get("enabled", False):
                                self._apis[item] = obj(api_config)
                                logging.info(f"已注册 API: {item} ({name})")
                            else:
                                logging.info(f"跳过已禁用的 API: {item}")
                except Exception as e:
                    logging.error(f"从 {item} 注册 API 失败: {e}")

    def get_api(self, name):
        return self._apis.get(name)

    def get_all_apis(self):
        return self._apis
