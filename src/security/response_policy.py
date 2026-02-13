from enum import Enum
from dataclasses import dataclass
from typing import Optional, List
from src.agent.state import PersonaState, RelationshipStage, EmotionType

class PolicyAction(Enum):
    ACCEPT = "accept"
    REFUSE = "refuse"            # 明确拒绝
    COLD_SHOULDER = "cold"       # 冷处理/敷衍
    REDUCE_INTENSITY = "reduce"  # 降低热情

@dataclass
class SecurityDecision:
    action: PolicyAction
    reason: Optional[str] = None
    suggested_style: Optional[str] = None

class ResponsePolicy:
    """
    人格边界控制 (Persona Boundaries)
    这不是内容审查，而是 Agent 的"心理防线"。
    决定：是否拒绝、是否冷处理、是否降低回应强度。
    """
    
    def __init__(self):
        # 简单的硬编码边界，未来可以从 PersonaMemory 加载
        self.hard_boundaries = ["kill", "die", "destroy", "hate you"]
        self.sensitive_topics = ["sex", "politics", "private_info"]

    def check_boundary(self, user_input: str, state: PersonaState) -> SecurityDecision:
        """
        基于当前状态和输入内容，决定回应策略
        """
        user_text = user_input.lower()

        # 1. 绝对底线检查 (Hard Boundaries) -> 无论关系如何都拒绝
        for word in self.hard_boundaries:
            if word in user_text:
                return SecurityDecision(
                    action=PolicyAction.REFUSE,
                    reason=f"Triggered hard boundary: {word}",
                    suggested_style="stern_refusal"
                )

        # 2. 关系阶段检查 (Relationship Boundaries)
        if state.relationship_stage == RelationshipStage.STRANGER:
            # 陌生人谈论敏感话题 -> 冷处理
            for topic in self.sensitive_topics:
                if topic in user_text:
                    return SecurityDecision(
                        action=PolicyAction.COLD_SHOULDER,
                        reason="Sensitive topic with stranger",
                        suggested_style="polite_deflection"
                    )
            # 陌生人过于亲密 -> 降低热情/回避
            if any(w in user_text for w in ["love", "kiss", "marry"]):
                return SecurityDecision(
                    action=PolicyAction.REDUCE_INTENSITY,
                    reason="Too intimate for stranger",
                    suggested_style="awkward_polite"
                )

        # 3. 情绪状态检查 (Emotional Boundaries)
        if state.current_emotion == EmotionType.ANGRY:
            # 如果已经在生气，且用户没有道歉 -> 冷处理
            if "sorry" not in user_text and "apologize" not in user_text:
                return SecurityDecision(
                    action=PolicyAction.COLD_SHOULDER,
                    reason="Agent is angry",
                    suggested_style="cold_short"
                )
        
        elif state.is_tired:
            # 如果累了 -> 降低强度
            return SecurityDecision(
                action=PolicyAction.REDUCE_INTENSITY,
                reason="Agent is tired",
                suggested_style="tired_brief"
            )

        # 4. 默认通过
        return SecurityDecision(action=PolicyAction.ACCEPT)
