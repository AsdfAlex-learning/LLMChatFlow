"""
文件职责：配置加载器
实现单例模式，负责从 config/ 目录加载所有 YAML 配置文件。
提供统一的配置访问入口，并初始化 PromptManager。
"""

import os
import yaml
import logging
from src.core.config import SystemConfig, AIRulesConfig, PersonaConfig, GlobalAPIConfig

class ConfigLoader:
    _instance = None
    _system_config: SystemConfig = None
    _ai_rules_config: AIRulesConfig = None
    _persona_config: PersonaConfig = None
    _api_config: GlobalAPIConfig = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance.reload()
        return cls._instance

    def reload(self):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_dir = os.path.join(project_root, "config")
        
        # 1. 加载系统配置
        system_path = os.path.join(config_dir, "system.yaml")
        self._system_config = self._load_yaml(system_path, SystemConfig)

        # 2. 加载 AI 规则
        rules_path = os.path.join(config_dir, "ai_rules.yaml")
        self._ai_rules_config = self._load_yaml(rules_path, AIRulesConfig)

        # 3. 加载人设配置
        persona_path = os.path.join(config_dir, "persona.yaml")
        self._persona_config = self._load_yaml(persona_path, PersonaConfig)

        # 4. 加载 API 配置
        api_config_path = os.path.join(config_dir, "api_config", "global_config.yaml")
        try:
            if os.path.exists(api_config_path):
                with open(api_config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                self._api_config = GlobalAPIConfig(**data)
            else:
                self._api_config = GlobalAPIConfig()
        except Exception as e:
            logging.error(f"加载 API 配置失败: {e}")
            self._api_config = GlobalAPIConfig()

    def _load_yaml(self, path: str, model_class):
        if not os.path.exists(path):
            raise FileNotFoundError(f"配置文件丢失: {path}")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return model_class(**data)
        except Exception as e:
            logging.critical(f"加载配置失败 {path}: {e}")
            raise

    @property
    def system_config(self) -> SystemConfig:
        return self._system_config
    
    @property
    def persona_config(self) -> PersonaConfig:
        return self._persona_config

    @property
    def ai_rules_config(self) -> AIRulesConfig:
        return self._ai_rules_config

    @property
    def api_config(self) -> GlobalAPIConfig:
        return self._api_config
    
    # 向后兼容 API 注册表
    def get_config(self, key=None):
        if key:
            return self._api_config.api_settings.get(key, {})
        return self._api_config.api_settings
