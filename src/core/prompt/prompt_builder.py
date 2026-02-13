"""
文件职责：Prompt 构建器
负责将系统规则、人设、记忆、对话历史和用户输入组装成最终发送给 LLM 的 Prompt。
统一了主动消息和被动回复的 Prompt 结构，确保系统行为的一致性。
"""

from typing import Optional
from src.core.config_loader import ConfigLoader

class PromptBuilder:
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader

    def build(self, 
              user_input: str, 
              context_str: str = "暂无", 
              memory_str: str = "暂无", 
              instruction: Optional[str] = None) -> str:
        """
        构建标准的 XML 格式 Prompt。
        
        Args:
            user_input: 用户的当前输入或特定的指令内容
            context_str: 近期对话历史摘要或原始内容
            memory_str: 相关记忆摘要
            instruction: 额外的动态指令（例如 Orchestrator 的风格指导）
            
        Returns:
            组装好的 Prompt 字符串
        """
        
        # 1. 获取静态配置
        ai_rules = self.config_loader.ai_rules_config.format()
        persona = self.config_loader.persona_config.default.format()
        
        # 2. 组装 System 部分
        system_section = f"""<system>
  <protocol>
{ai_rules}
  </protocol>
</system>"""

        # 3. 组装 Persona 部分
        persona_section = f"""<persona>
{persona}
</persona>"""

        # 4. 组装 Context 部分
        context_section = f"""<context>
  <memory type="summary">
{memory_str}
  </memory>

  <conversation type="recent">
{context_str}
  </conversation>
</context>"""

        # 5. 组装 Instruction 部分 (如果有)
        instruction_section = ""
        if instruction:
            instruction_section = f"""<instruction>
{instruction}
</instruction>"""

        # 6. 组装 User 部分
        user_section = f"""<user>
{user_input}
</user>"""

        # 7. 最终拼接
        # 注意：顺序很重要，通常 System -> Persona -> Context -> Instruction -> User
        final_prompt = f"{system_section}\n\n{persona_section}\n\n{context_section}\n\n{instruction_section}\n\n{user_section}"
        
        return final_prompt
