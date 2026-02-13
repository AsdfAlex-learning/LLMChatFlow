from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from src.agent.state import PersonaState, EmotionType, RelationshipStage

class MoodType(Enum):
    NEUTRAL = "neutral"
    SOFT = "soft"
    DISTANT = "distant"
    WARM = "warm"
    PLAYFUL = "playful"

class TextStrategy(Enum):
    SHORT_REPLY = "short_reply"
    LONG_REPLY = "long_reply"
    SILENCE = "silence"
    COMFORT = "comfort"

class BodyAction(Enum):
    IDLE = "idle"
    NOD = "nod"
    SHY = "shy"
    TILT_HEAD = "tilt_head"
    WAVE = "wave"

@dataclass
class ExpressionPlan:
    """
    表达计划
    决定了 Agent "想怎么回应"
    对应输出: { "mood": "...", "text_strategy": "...", "body_action": "..." }
    """
    mood: MoodType = MoodType.NEUTRAL
    text_strategy: TextStrategy = TextStrategy.SHORT_REPLY
    body_action: BodyAction = BodyAction.IDLE
    
    # 辅助字段
    should_reply: bool = True
    delay_ms: int = 500  # 拟人化延迟

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mood": self.mood.value,
            "text_strategy": self.text_strategy.value,
            "body_action": self.body_action.value
        }

class EmpathyPlanner:
    """
    情境/情绪/表达策略决策器 (The Prefrontal Cortex)
    
    职责：
    1. 决定态度 (Mood)
    2. 决定策略 (TextStrategy)
    3. 决定动作 (BodyAction)
    
    原则：
    - 不调用 LLM
    - 不生成文本
    - 纯规则驱动 (Rule-based)
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}

    def plan_response(self, user_input: str, current_state: PersonaState) -> ExpressionPlan:
        """
        从用户输入 + 当前状态中判断回应策略
        """
        # 1. 初始化默认计划
        plan = ExpressionPlan()
        
        # 预处理输入
        text_len = len(user_input)
        keywords = self._extract_keywords(user_input)
        
        # 2. 规则判断逻辑
        
        # 规则 A: 沉默/忽略策略
        # 如果输入为空或者是一些无意义的符号，可能选择沉默
        if text_len == 0:
            plan.text_strategy = TextStrategy.SILENCE
            plan.should_reply = False
            return plan

        # 规则 B: 关系阶段影响基调
        if current_state.relationship_stage in [RelationshipStage.CLOSE_FRIEND, RelationshipStage.PARTNER]:
            plan.mood = MoodType.WARM
        elif current_state.relationship_stage == RelationshipStage.STRANGER:
            plan.mood = MoodType.NEUTRAL

        # 规则 C: 关键词触发情绪与动作
        if any(w in user_input for w in ["喜欢", "爱", "cute", "love"]):
            plan.mood = MoodType.SOFT
            plan.body_action = BodyAction.SHY
            plan.text_strategy = TextStrategy.SHORT_REPLY # 害羞时话少
            
        elif any(w in user_input for w in ["笨蛋", "傻", "讨厌"]):
            plan.mood = MoodType.DISTANT
            plan.body_action = BodyAction.TILT_HEAD
            
        elif any(w in user_input for w in ["救命", "难过", "哭", "help", "sad"]):
            plan.mood = MoodType.SOFT
            plan.text_strategy = TextStrategy.COMFORT
            plan.body_action = BodyAction.NOD
            
        # 规则 D: 输入长度影响回复策略
        elif text_len > 50:
            # 用户说了很长一段话，我们需要倾听并给出较长回应
            plan.text_strategy = TextStrategy.LONG_REPLY
            plan.body_action = BodyAction.NOD
            plan.delay_ms = 1500 # 读得慢一点
            
        elif text_len < 5:
            # 用户只说了几个字，我们也简单回应
            plan.text_strategy = TextStrategy.SHORT_REPLY
            if plan.body_action == BodyAction.IDLE:
                plan.body_action = BodyAction.NOD
            plan.delay_ms = 500

        # 规则 E: 状态修正
        # 如果 Agent 处于特定情绪状态，会覆盖上述判断
        if current_state.current_emotion == EmotionType.ANGRY:
            plan.mood = MoodType.DISTANT
            plan.text_strategy = TextStrategy.SHORT_REPLY
            
        return plan

    def _extract_keywords(self, text: str) -> list:
        # 简单的关键词提取，未来可以换成更高级的
        return text.lower().split()
