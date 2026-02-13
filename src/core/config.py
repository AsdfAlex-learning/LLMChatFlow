"""
文件职责：系统配置模型
定义了系统所有配置文件的 Pydantic 数据模型。
包括 system.yaml, ai_rules.yaml, persona.yaml 等文件的结构验证。
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

# ================== 系统配置模型 (system.yaml) ==================

class TelegramConfig(BaseModel):
    bot_token: str = Field(..., description="Telegram 机器人的 Token")
    owner_id: int = Field(default=0, description="拥有绝对控制权的 Owner ID")

class LLMConfig(BaseModel):
    api_key: str = Field(..., description="OpenAI 兼容的 API Key")
    api_url: str = Field(default="https://api.deepseek.com/chat/completions", description="API 地址")
    model: str = Field(default="deepseek-chat", description="模型名称")
    temperature: float = Field(default=0.7, description="采样温度")
    max_tokens: int = Field(default=1024, description="回复最大 Token 数")
    use_local_api: bool = Field(default=False, description="是否使用本地 API")
    local_api_url: str = Field(default="http://localhost:8000/v1/chat/completions", description="本地 API 地址")

class BotConfig(BaseModel):
    private_mode_default: bool = Field(default=True, description="默认私有模式状态")

class MessageBufferConfig(BaseModel):
    collect_min_time: int = Field(default=15, description="最小收集时间 (秒)")
    collect_max_time: int = Field(default=20, description="最大收集时间 (秒)")

class LLMServerConfig(BaseModel):
    host: str = Field(default="0.0.0.0", description="Server Host")
    port: int = Field(default=8000, description="Server Port")
    model_name_or_path: str = Field(default="deepseek-ai/deepseek-llm-7b-chat", description="Model Path")
    quantization: Optional[str] = Field(default="4bit", description="Quantization (4bit/8bit/none)")

class ProactiveConfig(BaseModel):
    check_interval_min: int = Field(default=1800, description="检查间隔最小值 (秒)")
    check_interval_max: int = Field(default=7200, description="检查间隔最大值 (秒)")
    send_delay_min: int = Field(default=60, description="发送延迟最小值 (秒)")
    send_delay_max: int = Field(default=600, description="发送延迟最大值 (秒)")

class SystemConfig(BaseModel):
    telegram: TelegramConfig
    llm: LLMConfig
    llm_server: LLMServerConfig = Field(default_factory=LLMServerConfig)
    bot: BotConfig = Field(default_factory=BotConfig)
    message_buffer: MessageBufferConfig = Field(default_factory=MessageBufferConfig)
    proactive: ProactiveConfig = Field(default_factory=ProactiveConfig)

# ================== AI 规则模型 (ai_rules.yaml) ==================

class AIRulesConfig(BaseModel):
    rules: List[str] = Field(default_factory=list, description="系统级 AI 规则列表")

    def format(self) -> str:
        return "\n".join([f"- {rule}" for rule in self.rules])

# ================== 人设模型 (persona.yaml) ==================

class IdentityConfig(BaseModel):
    name: str
    description: str

class RelationshipConfig(BaseModel):
    type: str
    closeness: str
    power_distance: str

class PersonalityConfig(BaseModel):
    emotionality: str
    stability: str
    initiative: str

class LanguageStyleConfig(BaseModel):
    tone: str
    fillers: List[str]
    punctuation: str

class PersonaSettings(BaseModel):
    identity: IdentityConfig
    relationship: RelationshipConfig
    personality: PersonalityConfig
    language_style: LanguageStyleConfig
    boundaries: List[str] = Field(default_factory=list)

    def format(self) -> str:
        lines = []
        lines.append(f"姓名: {self.identity.name}")
        lines.append(f"设定: {self.identity.description}")
        
        lines.append(f"关系类型: {self.relationship.type}")
        lines.append(f"亲密度: {self.relationship.closeness}")
        lines.append(f"权力距离: {self.relationship.power_distance}")
        
        lines.append(f"性格特征: 感性度({self.personality.emotionality}), 稳定性({self.personality.stability}), 主动性({self.personality.initiative})")
        
        lines.append(f"语言风格: {self.language_style.tone}")
        lines.append(f"口癖/填充词: {', '.join(self.language_style.fillers)}")
        lines.append(f"标点习惯: {self.language_style.punctuation}")
        
        if self.boundaries:
            lines.append("行为边界:")
            for b in self.boundaries:
                lines.append(f"  - {b}")
        return "\n".join(lines)

class PersonaConfig(BaseModel):
    # 允许动态键以支持不同的人设，'default' 是必须的
    default: PersonaSettings
    extra_personas: Dict[str, PersonaSettings] = Field(default_factory=dict)

    def __init__(self, **data):
        # 显式处理 'default'，将其他放入 extra_personas
        default_data = data.pop('default', None)
        if default_data is None:
             raise ValueError("persona.yaml 必须包含 'default' 键")
        
        super().__init__(default=default_data, extra_personas=data)

# ================== API 配置模型 ==================

class GlobalAPIConfig(BaseModel):
    api_settings: Dict[str, Any] = Field(default_factory=dict)
