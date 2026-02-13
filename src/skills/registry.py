from typing import Dict, Type, Optional, Any
from .base import BaseSkill

class SkillRegistry:
    """
    Skill 注册中心。
    负责 Skill 的注册、查找和统计。
    """
    
    _skills: Dict[str, BaseSkill] = {}
    _intent_map: Dict[str, str] = {}
    _usage_stats: Dict[str, int] = {}
    
    # MLflow logger hook (optional)
    _logger_hook: Optional[Any] = None

    @classmethod
    def register(cls, skill: BaseSkill, intents: list[str] = None):
        """
        注册一个 Skill。
        
        Args:
            skill: Skill 实例。
            intents: 触发该 Skill 的意图列表（可选）。
        """
        cls._skills[skill.name] = skill
        cls._usage_stats[skill.name] = 0
        
        if intents:
            for intent in intents:
                cls._intent_map[intent] = skill.name
                
        print(f"Registered Skill: {skill.name} (Intents: {intents})")

    @classmethod
    def get_skill(cls, name: str) -> Optional[BaseSkill]:
        """按名称查找 Skill"""
        return cls._skills.get(name)

    @classmethod
    def get_skill_by_intent(cls, intent: str) -> Optional[BaseSkill]:
        """按意图查找 Skill"""
        skill_name = cls._intent_map.get(intent)
        if skill_name:
            return cls._skills.get(skill_name)
        return None

    @classmethod
    def run(cls, skill_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 Skill 并记录统计信息。
        """
        skill = cls.get_skill(skill_name)
        if not skill:
            raise ValueError(f"Skill '{skill_name}' not found")
            
        # 统计调用次数
        cls._usage_stats[skill_name] += 1
        
        # 执行前 hook (e.g. log to MLflow)
        if cls._logger_hook:
            cls._logger_hook.log_skill_usage(skill_name, input_data)
            
        try:
            result = skill.run(input_data)
            return result
        except Exception as e:
            # 简单的错误包装
            return {
                "error": str(e),
                "skill": skill_name,
                "status": "failed"
            }
            
    @classmethod
    def set_logger(cls, logger):
        cls._logger_hook = logger

    @classmethod
    def get_all_skills(cls) -> Dict[str, BaseSkill]:
        return cls._skills
