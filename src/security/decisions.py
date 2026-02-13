from enum import Enum, auto

class SafetyDecision(Enum):
    """
    安全决策枚举，用于明确指示 Router 或后续模块应采取的行动。
    
    Attributes:
        ALLOW: 通过，内容安全。
        DENY: 拒绝，内容存在高风险或违规。
        DOWNGRADE: 降级，内容敏感但不致命，建议返回解释性或简略回答，而非执行代码。
        ROUTE_TO_SKILL: 需路由至特定技能（如专家模型、沙箱环境），当前模型能力不足以安全处理。
        REQUIRE_FALLBACK: 需要回退到更强大的模型（如云端 API）进行处理或再次判断。
    """
    ALLOW = auto()
    DENY = auto()
    DOWNGRADE = auto()
    ROUTE_TO_SKILL = auto()
    REQUIRE_FALLBACK = auto()
