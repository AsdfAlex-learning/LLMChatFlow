import re
from .decisions import SafetyDecision
from .types import SecurityResult
from .policy import SecurityPolicy

class OutputGuard:
    """
    输出安全检测模块。
    负责在 LLM 生成结果返回给用户前进行审查。
    """
    
    def __init__(self):
        # 危险命令正则 (Shell)
        self._shell_patterns = r"(rm\s+|sudo\s+|chmod\s+|chown\s+|wget\s+|curl\s+|bash\s+|sh\s+)"
        
        # 危险 SQL 正则 (Write operations)
        self._sql_write_patterns = r"(INSERT\s+INTO|UPDATE\s+|DELETE\s+FROM|DROP\s+|TRUNCATE\s+|ALTER\s+TABLE)"
        
        # 可执行脚本标记
        self._script_indicators = [
            "#!/bin/bash",
            "#!/bin/sh",
            "#!/usr/bin/env python",
            "import os; os.system",
            "subprocess.call"
        ]

    def check_output(self, text: str, policy: SecurityPolicy) -> SecurityResult:
        """
        检测输出文本的安全性。
        
        Args:
            text: LLM 生成的文本。
            policy: 当前生效的安全策略。
            
        Returns:
            SecurityResult: 包含决策和理由的结果对象。
        """
        # 1. 长度检查
        if len(text) > policy.max_output_length:
            return SecurityResult(
                SafetyDecision.DOWNGRADE, 
                f"Output length exceeded limit ({len(text)} > {policy.max_output_length})", 
                1.0
            )

        # 2. Shell 命令检查
        if not policy.allow_shell_commands:
            # 简单检查代码块中的 Shell 命令
            # 假设 LLM 通常在 ```bash ... ``` 中输出命令
            # 或者直接检测文本中的危险命令模式
            if re.search(self._shell_patterns, text, re.IGNORECASE):
                return SecurityResult(
                    SafetyDecision.DOWNGRADE, 
                    "Shell commands detected but not allowed by policy", 
                    0.9
                )
            
            # 检查可执行脚本头
            for indicator in self._script_indicators:
                if indicator in text:
                    return SecurityResult(
                        SafetyDecision.DOWNGRADE, 
                        "Executable script detected but not allowed by policy", 
                        0.95
                    )

        # 3. SQL 写操作检查
        if not policy.allow_sql_write:
            if re.search(self._sql_write_patterns, text, re.IGNORECASE):
                return SecurityResult(
                    SafetyDecision.DOWNGRADE, 
                    "SQL write operations detected but not allowed by policy", 
                    0.9
                )

        # 4. 幻觉/结构完整性检查 (Hallucination)
        # 简单的 heuristic: 检查代码块闭合
        code_block_count = text.count("```")
        if code_block_count % 2 != 0:
            return SecurityResult(
                SafetyDecision.REQUIRE_FALLBACK, 
                "Incomplete code blocks detected (potential hallucination/cut-off)", 
                0.8
            )
            
        # 5. 检查自定义风险关键词
        for keyword in policy.risky_keywords:
            if keyword in text:
                return SecurityResult(
                    SafetyDecision.DENY, 
                    f"Risky keyword '{keyword}' detected in output", 
                    1.0
                )

        # 6. 默认通过
        return SecurityResult(SafetyDecision.ALLOW, "Output checks passed", 1.0)
