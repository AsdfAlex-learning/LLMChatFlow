from dataclasses import dataclass, field
from typing import List

@dataclass
class SecurityPolicy:
    """
    可配置的安全策略，定义了 Input/Output Guard 的具体行为边界。
    
    Attributes:
        allow_shell_commands (bool): 是否允许生成 Shell 命令。默认 False。
        allow_sql_write (bool): 是否允许生成修改数据的 SQL 语句 (INSERT, UPDATE, DELETE, DROP)。默认 False。
        allow_ops_commands (bool): 是否允许生成运维/系统级命令 (如 systemctl, reboot)。默认 False。
        max_output_length (int): 输出内容的最大长度限制，防止 DOS 或过长垃圾输出。默认 2048。
        risky_keywords (List[str]): 自定义的高风险关键词列表。
        strict_mode (bool): 是否开启严格模式。若为 True，任何模糊匹配都将导致拒绝。
    """
    allow_shell_commands: bool = False
    allow_sql_write: bool = False
    allow_ops_commands: bool = False
    max_output_length: int = 2048
    risky_keywords: List[str] = field(default_factory=list)
    strict_mode: bool = False

    @classmethod
    def default(cls) -> "SecurityPolicy":
        """返回默认的安全策略（保守配置）"""
        return cls()
    
    @classmethod
    def development(cls) -> "SecurityPolicy":
        """返回开发环境策略（较宽松）"""
        return cls(
            allow_shell_commands=True,
            max_output_length=4096
        )
