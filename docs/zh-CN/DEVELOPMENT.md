# Telegram 情感伴侣机器人 - 开发文档 (Development Guide)

本文档旨在为开发者提供项目的技术架构、环境搭建、核心逻辑及开发流程的正式说明。

---

## 1. 项目概述 (Overview)

本项目是一个基于 Python 的 Telegram 情感伴侣机器人，旨在通过模拟人类的情感交互模式（如碎片化回复、情绪感知、关系演变）提供深度的陪伴体验。

### 核心特性
- **拟人化交互**：支持碎片化消息发送、模拟打字延迟、主动发起话题。
- **情感计算**：内置 `EmpathyPlanner`（共情规划器），根据用户输入和当前状态决定回复策略（如安慰、共鸣、吐槽）。
- **长期记忆**：基于 SQLite 的记忆存储，支持短期上下文与长期摘要记忆的动态融合。
- **模块化架构**：采用 Kernel-Satellite 架构，核心逻辑与通信协议分离，便于扩展和测试。

---

## 2. 环境搭建 (Setup)

### 前置要求
- **Python**: 3.12+
- **Conda**: 推荐使用 Conda 管理虚拟环境。
- **Telegram Bot Token**: 从 @BotFather 获取。
- **LLM API Key**: 支持 DeepSeek 或其他 OpenAI 兼容接口。

### 安装步骤

1.  **克隆项目**
    ```bash
    git clone <repository_url>
    cd Telegram_Chatbot
    ```

2.  **创建环境**
    使用项目根目录下的 `environment.yaml` 创建 Conda 环境：
    ```bash
    conda env create -f environment.yaml
    conda activate telegram_bot
    ```

3.  **配置环境**
    在 `config/` 目录下创建必要的配置文件（参考 `config/example_system.yaml`）：
    
    *   **system.yaml** (系统配置):
        ```yaml
        system:
          superuser_id: 123456789  # 管理员 ID
          llm_server:
            base_url: "https://api.deepseek.com"
            api_key: "sk-..."
            model: "deepseek-chat"
        ```
    *   **ai_rules.yaml** (AI 行为准则): 定义系统的核心 Prompt 约束。
    *   **persona.yaml** (人设配置): 定义机器人的性格、背景故事。

---

## 3. 项目架构 (Architecture)

项目采用 **Kernel-Satellite** 模式，核心业务逻辑（src/core, src/agent）不依赖于具体的 Bot 平台（Telegram），通过 `src/bot` 层进行适配。

### 目录结构

```text
src/
├── agent/                  # [智能体层] 负责思考与决策
│   ├── empathy_planner.py  # 共情规划器 (决定 Mood, Strategy)
│   ├── orchestrator.py     # 表达编排器 (调用 LLM, 执行 Skill)
│   └── state.py            # 状态定义 (PersonaState)
├── core/                   # [核心层] 基础设施与业务流
│   ├── chat_service.py     # 聊天服务 (串联 Agent 与 Memory)
│   ├── interaction.py      # 交互管理 (缓冲用户消息, 节奏控制)
│   ├── prompt/             # Prompt 工程
│   │   └── prompt_builder.py # 统一 XML Prompt 构建器
│   └── memory/             # 记忆系统 (Repository, Service)
├── bot/                    # [适配层] Telegram 协议适配
│   ├── app.py              # Bot 应用入口
│   ├── wiring.py           # 依赖注入 (DI) 容器
│   └── telegram/           # Telebot 处理器与轮询逻辑
├── skills/                 # [技能层] 外部能力插件 (天气, 搜索等)
└── llm_system/             # [模型层] 本地模型训练与推理 (可选)
```

### 核心流程 (Data Flow)

1.  **接收消息**: `src/bot/telegram/handler` 接收用户消息，推送到 `InteractionManager`。
2.  **缓冲与节奏**: `InteractionManager` 缓冲短时间内的多条消息，模拟人类阅读习惯。
3.  **核心处理**:
    *   `ChatService` 获取用户状态 (`PersonaState`) 和记忆 (`MemoryService`)。
    *   调用 `EmpathyPlanner` 分析用户意图，生成 `ExpressionPlan`（包含情绪、策略）。
    *   `ExpressionOrchestrator` 根据计划，调用 `PromptBuilder` 组装 XML Prompt。
    *   请求 LLM API 生成文本。
4.  **响应执行**: `Orchestrator` 解析 LLM 响应，拆分为碎片化消息，通过 `Bot Adapter` 发回。

---

## 4. 开发指南 (Development)

### 4.1 修改 Prompt 逻辑
所有的 Prompt 构建逻辑均收敛于 `src/core/prompt/prompt_builder.py`。
- 若要修改 System Prompt 结构，请编辑 `build()` 方法中的 XML 模板。
- 若要修改具体内容，请调整 `config/ai_rules.yaml` 和 `config/persona.yaml`。

### 4.2 添加新技能 (Skills)
1.  在 `src/skills/` 下创建新的技能类（继承自 BaseSkill）。
2.  在 `ExpressionOrchestrator` 中注册该技能。
3.  在 `config/ai_rules.yaml` 中告知 LLM 具备该能力（Function Calling 定义）。


## 5. 部署与维护 (Deployment)

### 启动服务
```bash
python main.py
```

### 常见问题
- **依赖缺失**: 请确保 `conda activate telegram_bot` 已激活。
- **配置文件错误**: `ConfigLoader` 会在启动时校验 `config/system.yaml` 等文件是否存在。
- **Prompt 异常**: 检查日志中 `PromptBuilder` 生成的最终 Prompt 是否符合预期 XML 结构。

---

## 6. 贡献规范 (Contribution)

- **代码风格**: 遵循 PEP 8 规范。
- **提交信息**: 使用 Conventional Commits (e.g., `feat: add memory consolidation`, `fix: prompt builder xml tag`).
- **文档**: 修改核心逻辑后，请同步更新本文档及 `PROJECT_REVIEW.md`。

---
*Last Updated: 2026-02-08*
