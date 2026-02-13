from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any

class EmotionType(Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SHY = "shy"
    EXCITED = "excited"

class RelationshipStage(Enum):
    STRANGER = "stranger"       # 陌生
    ACQUAINTANCE = "acquaintance" # 认识
    FRIEND = "friend"           # 熟悉
    CLOSE_FRIEND = "close_friend" # 信任
    PARTNER = "partner"         # 依赖

@dataclass
class PersonaState:
    """
    人格状态模型 (The Agent's Inner State)
    维护 Agent 的核心情绪和关系状态
    """
    # 核心情绪维度
    current_emotion: EmotionType = EmotionType.NEUTRAL
    arousal_level: float = 0.5  # 唤醒度 0.0 - 1.0
    valence_level: float = 0.5  # 愉悦度 0.0 - 1.0
    
    # 关系状态 (陌生 / 熟悉 / 信任)
    relationship_stage: RelationshipStage = RelationshipStage.STRANGER
    intimacy_level: int = 0  # 亲密度数值
    
    # 短期状态标志
    is_tired: bool = False
    is_busy: bool = False
    
    @property
    def is_trusted(self) -> bool:
        """是否处于信任阶段"""
        return self.relationship_stage in [RelationshipStage.CLOSE_FRIEND, RelationshipStage.PARTNER]

    def update_emotion(self, emotion: EmotionType, arousal: float = None):
        """更新当前情绪"""
        self.current_emotion = emotion
        if arousal is not None:
            self.arousal_level = arousal
            
    def update_relationship(self, stage: RelationshipStage, intimacy_delta: int = 0):
        """更新关系状态"""
        self.relationship_stage = stage
        self.intimacy_level += intimacy_delta

    def to_dict(self) -> Dict[str, Any]:
        return {
            "emotion": self.current_emotion.value,
            "arousal": self.arousal_level,
            "relationship": self.relationship_stage.value,
            "intimacy": self.intimacy_level,
            "is_trusted": self.is_trusted
        }
