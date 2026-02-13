from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseSkill(ABC):
    """
    Skill 抽象基类。
    所有 Skill 必须继承此类并实现 run 方法。
    
    Attributes:
        name (str): 技能唯一标识符。
        description (str): 技能描述。
        input_schema (Dict[str, Any]): 输入数据结构描述（便于验证和文档化）。
        output_schema (Dict[str, Any]): 输出数据结构描述。
        risk_level (str): 风险等级 ('low', 'medium', 'high')。
    """
    
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    risk_level: str

    def __init__(self):
        # 默认元数据，子类应覆盖
        if not hasattr(self, 'name'):
            raise NotImplementedError("Skill must define 'name'")
        if not hasattr(self, 'description'):
            raise NotImplementedError("Skill must define 'description'")
        if not hasattr(self, 'risk_level'):
            self.risk_level = 'low'

    @abstractmethod
    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行技能逻辑。
        
        Args:
            input_data: 符合 input_schema 的输入数据。
            
        Returns:
            符合 output_schema 的输出数据。
        """
        pass

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        简单的输入验证（可扩展为 JSON Schema 验证）。
        目前仅作为 Hook 存在。
        """
        return True
