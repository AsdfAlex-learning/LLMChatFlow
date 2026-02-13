from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import random

from src.agent.state import PersonaState
from src.agent.empathy_planner import EmpathyPlanner, ExpressionPlan, TextStrategy, BodyAction
from src.core.llm_client import LLMClient
from src.core.prompt.prompt_builder import PromptBuilder

# Text Skills
from src.skills.text.short_reply import short_reply_strategy
from src.skills.text.long_reply import long_emotional_reply_strategy
from src.skills.text.comfort import comfort_reply_strategy

# Body Language Skills
from src.skills.body_language.idle import idle_action
from src.skills.body_language.nod import nod_action
from src.skills.body_language.shy import shy_action
from src.skills.body_language.tilt_head import tilt_head_action
from src.skills.body_language.wave import wave_action

@dataclass
class AgentResponse:
    """
    Agent 的最终表达结果
    包含：说什么(text)、做什么(action)、怎么说(voice/mood)
    """
    text: str
    action: str
    mood: str
    delay_ms: int
    voice_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "action": self.action,
            "mood": self.mood,
            "delay_ms": self.delay_ms,
            "voice": self.voice_params
        }

class ExpressionOrchestrator:
    """
    多模态表达编排器 (The Conductor)
    
    职责：
    1. 接收 Planner 的 ExpressionPlan
    2. 调用 Text Skills 获取生成策略
    3. 调用 Body Skills 获取动作指令
    4. 调用 LLM 生成最终文本
    5. 组装成 AgentResponse
    """
    
    def __init__(self, planner: EmpathyPlanner, llm_client: LLMClient, prompt_builder: PromptBuilder):
        self.planner = planner
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder

    def orchestrate_response(self, user_input: str, state: PersonaState, context_str: str = "", memory_str: str = "") -> Optional[AgentResponse]:
        """
        编排一次完整的响应
        """
        # 1. 获取决策计划
        plan = self.planner.plan_response(user_input, state)
        
        # 如果策略是保持沉默，则不返回响应
        if not plan.should_reply or plan.text_strategy == TextStrategy.SILENCE:
            return None
            
        # 2. 执行 Body Language Skill
        action_name = self._execute_body_skill(plan.body_action)
        
        # 3. 执行 Text Skill (获取生成策略)
        text_config = self._execute_text_skill(plan.text_strategy, user_input)
        
        # 4. 生成文本
        generated_text = self._generate_text(text_config, user_input, context_str, memory_str)
        
        # 5. 组装最终响应
        response = AgentResponse(
            text=generated_text,
            action=action_name,
            mood=plan.mood.value,
            delay_ms=plan.delay_ms,
            voice_params={"tone": plan.mood.value} # 简单示例
        )
        
        return response

    def _generate_text(self, text_config: Dict[str, Any], user_input: str, context_str: str, memory_str: str) -> str:
        """调用 LLM 生成文本"""
        
        # 获取风格指令
        style_instruction = text_config.get("style_instruction", "")
        
        # 使用 PromptBuilder 构建 Prompt
        # 这将自动包含 System Rules, Persona, Memory, Context
        final_prompt = self.prompt_builder.build(
            user_input=user_input,
            context_str=context_str,
            memory_str=memory_str,
            instruction=style_instruction
        )
        
        messages = [
            {"role": "user", "content": final_prompt}
        ]
        
        try:
            return self.llm_client.chat_completion(
                messages=messages,
                temperature=text_config.get("temperature", 0.7),
                max_tokens=text_config.get("max_tokens", 150)
            )
        except Exception as e:
            # Fallback
            return "I'm sorry, I couldn't think of what to say."

    def _execute_body_skill(self, action_type: BodyAction) -> str:
        """根据动作类型调用对应的 Skill 函数"""
        if action_type == BodyAction.IDLE:
            return idle_action()
        elif action_type == BodyAction.NOD:
            return nod_action()
        elif action_type == BodyAction.SHY:
            return shy_action()
        elif action_type == BodyAction.TILT_HEAD:
            return tilt_head_action()
        elif action_type == BodyAction.WAVE:
            return wave_action()
        else:
            return idle_action()

    def _execute_text_skill(self, strategy: TextStrategy, user_input: str) -> Dict[str, Any]:
        """根据文本策略调用对应的 Skill 函数"""
        if strategy == TextStrategy.SHORT_REPLY:
            return short_reply_strategy(user_input)
        elif strategy == TextStrategy.LONG_REPLY:
            return long_emotional_reply_strategy(user_input)
        elif strategy == TextStrategy.COMFORT:
            return comfort_reply_strategy(user_input)
        else:
            return short_reply_strategy(user_input)
