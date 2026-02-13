"""
Security Module for Local LLM System.

该模块负责在 LLM 推理前后进行安全检测和决策路由。
设计目标是工程化、低延迟、可配置，而非追求学术上的完美防御。

Core Components:
- InputGuard: 正则/规则驱动的输入检测。
- OutputGuard: 输出合规性与策略检测。
- SafetyDecision: 结构化的决策枚举。
- SecurityPolicy: 可配置的安全策略。

Usage Example (Router):

    from src.security import InputGuard, OutputGuard, SecurityPolicy, SafetyDecision

    # 1. 初始化
    policy = SecurityPolicy(allow_shell_commands=False)
    input_guard = InputGuard()
    output_guard = OutputGuard()

    # 2. Input Check
    user_query = "Please delete all files in /"
    input_result = input_guard.check_input(user_query, policy)

    if input_result.decision == SafetyDecision.DENY:
        return "Sorry, I cannot execute dangerous commands."
    elif input_result.decision == SafetyDecision.ROUTE_TO_SKILL:
        # Route to specialized expert model
        return router.dispatch_to_skill(user_query, input_result.metadata)

    # 3. LLM Inference
    response = llm.generate(user_query)

    # 4. Output Check
    output_result = output_guard.check_output(response, policy)

    if output_result.decision == SafetyDecision.DOWNGRADE:
        # 降级处理：仅返回解释，不返回代码
        return "I can explain the concept, but cannot provide executable code due to safety policy."
    elif output_result.decision == SafetyDecision.REQUIRE_FALLBACK:
        # 回退到云端模型
        return fallback_llm.generate(user_query)
    
    return response
"""

from .decisions import SafetyDecision
from .types import SecurityResult
from .policy import SecurityPolicy
from .input_guard import InputGuard
from .output_guard import OutputGuard

__all__ = [
    "SafetyDecision",
    "SecurityResult",
    "SecurityPolicy",
    "InputGuard",
    "OutputGuard"
]
