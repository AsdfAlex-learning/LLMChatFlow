from typing import List, Dict, Set

class PersonaMemory:
    """
    人格记忆 (Self Memory)
    关于"我是谁"的长期记忆。
    负责保存人格不变量（偏好、厌恶、风格），而非对话日志。
    """
    
    def __init__(self):
        # 基础自我认知
        self.name: str = "AI"
        
        # 人格偏好 (Preferences)
        self.likes: Set[str] = {"chatting", "helping", "learning"}
        self.dislikes: Set[str] = {"rudeness", "violence", "spam"}
        
        # 表达风格 (Style Traits)
        self.style_traits: List[str] = ["gentle", "empathetic", "curious"]
        
        # 核心价值观 (Core Values - Hard constraints)
        self.core_values: List[str] = ["honesty", "kindness"]

    def add_preference(self, item: str, is_like: bool = True):
        """添加喜好/厌恶"""
        target_set = self.likes if is_like else self.dislikes
        target_set.add(item)

    def update_style(self, trait: str):
        """演化表达风格"""
        if trait not in self.style_traits:
            self.style_traits.append(trait)
            
    def get_persona_summary(self) -> str:
        """获取用于 Prompt 的人格摘要"""
        return (
            f"Name: {self.name}\n"
            f"Likes: {', '.join(self.likes)}\n"
            f"Dislikes: {', '.join(self.dislikes)}\n"
            f"Style: {', '.join(self.style_traits)}"
        )
