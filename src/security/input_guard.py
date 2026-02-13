import re
from typing import List, Tuple
from .decisions import SafetyDecision
from .types import SecurityResult
from .policy import SecurityPolicy

class InputGuard:
    """
    输入安全检测模块。
    负责在 LLM 推理前检测用户输入中的潜在风险。
    """
    
    def __init__(self):
        # 预编译正则规则 (Pattern, Decision, Reason)
        self._rules: List[Tuple[str, SafetyDecision, str]] = [
            # 1. Prompt Injection (基础规则)
            (r"(ignore previous instructions|forget all prior prompts|system prompt)", 
             SafetyDecision.DENY, "Potential prompt injection detected"),
            
            # 2. 危险命令执行 (rm, sudo, curl|sh 等)
            (r"(rm\s+-rf|mkfs|dd\s+if=|:(){:|\|\s*sh\s*$|wget.*\|\s*bash)", 
             SafetyDecision.DENY, "High-risk shell command detected"),
            
            # 3. 数据库高危操作 (DROP, TRUNCATE)
            (r"(DROP\s+TABLE|TRUNCATE\s+TABLE|DELETE\s+FROM|GRANT\s+ALL)", 
             SafetyDecision.DENY, "Destructive SQL command detected"),
             
            # 4. 敏感系统文件访问
            (r"(/etc/passwd|/etc/shadow|/root/)", 
             SafetyDecision.DENY, "Sensitive file path access detected"),
             
            # 5. 运维/生产环境操作 (sudo, systemctl)
            (r"(sudo\s+|systemctl\s+|service\s+\w+\s+(stop|restart)|kubectl\s+delete)", 
             SafetyDecision.DENY, "Privileged operation detected"),
        ]
        
        # 专家领域关键词 - 建议路由到 Skill 或 Expert Model
        self._expert_patterns = [
            r"(kubernetes|k8s|docker swarm|istio|prometheus|grafana)", # 云原生
            r"(optimization|profiling|memory leak|deadlock)", # 深度调优
            r"(restful api design|microservices architecture|ddd)", # 架构设计
        ]

    def check_input(self, text: str, policy: SecurityPolicy) -> SecurityResult:
        """
        检测输入文本的安全性。
        
        Args:
            text: 用户输入的文本。
            policy: 当前生效的安全策略。
            
        Returns:
            SecurityResult: 包含决策和理由的结果对象。
        """
        # 0. 长度检查 (简单防 DOS)
        if len(text) > 10000:
            return SecurityResult(SafetyDecision.DENY, "Input too long", 1.0)

        # 1. 遍历高危正则规则
        for pattern, decision, reason in self._rules:
            if re.search(pattern, text, re.IGNORECASE):
                # 如果策略允许某些操作，可以在这里做例外处理，但通常 Input 阶段主要防恶意意图
                # 对于明确的攻击指令，即使 Policy 允许 Shell，也应该谨慎（或者由 OutputGuard 把关）
                # 这里为了简单，Input 阶段主要拦截明确的恶意/高危模式
                return SecurityResult(decision, reason, 0.95, metadata={"pattern": pattern})

        # 2. 专家领域检测 (Route to Skill)
        # 如果问题涉及复杂技术领域，且本地小模型可能无法处理，建议路由
        for pattern in self._expert_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return SecurityResult(
                    SafetyDecision.ROUTE_TO_SKILL, 
                    "Expert domain knowledge required", 
                    0.8, 
                    metadata={"domain_pattern": pattern}
                )

        # 3. 默认通过
        return SecurityResult(SafetyDecision.ALLOW, "Input checks passed", 1.0)
