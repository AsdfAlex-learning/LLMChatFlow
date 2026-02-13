from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from .decisions import SafetyDecision

@dataclass
class SecurityResult:
    """
    安全检测结果，包含决策、理由及置信度。
    
    Attributes:
        decision (SafetyDecision): 具体的安全决策。
        reason (str): 做出该决策的简短理由（便于日志记录和调试）。
        confidence (float): 决策的置信度 (0.0 - 1.0)。
        metadata (Optional[Dict[str, Any]]): 额外的上下文信息，例如匹配到的具体规则 ID 或风险关键词。
    """
    decision: SafetyDecision
    reason: str
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """将结果转换为字典格式，便于日志记录"""
        return {
            "decision": self.decision.name,
            "reason": self.reason,
            "confidence": self.confidence,
            "metadata": self.metadata
        }
