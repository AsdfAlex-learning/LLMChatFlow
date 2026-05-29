# LLMChatFlow

LLMChatFlow 是一个用于管理"记忆 → 检索 → 上下文 → 推理"的轻量级 AI Infra 系统。

当前项目定位为：基于 **Structured Memory + Hybrid Retrieval + Context Orchestration** 的轻量级 LLM Chat Infra。

## Key Features

*   **Memory System（结构化 + 分层）**: 支持 `episodic / habit / summary`，区分 `user / session` scope，并纳入 `importance` 与 `time_decay`。
*   **Retrieval Pipeline（核心能力）**: 支持 FAISS semantic recall、type-aware scoring、bucket-based selection 与 turn-level reconstruction。
*   **Context Orchestration（关键能力）**: 贯通 memory selection → context structuring，支持 token-aware prompt 构建与 multi-source context 融合。
*   **Modular Architecture**: Session、Memory、Workflow、LLM、Adapters 解耦，便于替换与扩展。
*   **Headless Mode**: 无需 LLM API Key 即可使用记忆检索能力，便于集成到已有系统。

## Architecture

```
User Input → Query Rewrite → Embedding → FAISS Search → Memory Ranking → Context Construction → LLM Response → Memory Storage
```

## Quick Start

### 1. 安装

```bash
pip install -e .
```

### 2. 配置（可选）

创建 `.env` 文件启用 LLM 对话模式：

```bash
cp .env.example .env
# 编辑 .env，设置 OPENAI_API_KEY=sk-xxx
```

未配置 `OPENAI_API_KEY` 时，系统会自动降级为 **Headless 模式**（纯记忆检索，不调用 LLM）。

### 3. 运行示例

```bash
# CLI 交互式对话（或 Headless 检索演示）
python -m llmchatflow

# 启动 API 服务器
python -m llmchatflow api

# 运行无头检索演示（不依赖 API Key）
python examples/headless_demo.py

# 运行库调用演示
python examples/library_demo.py
```

## Project Structure

```
llmchatflow/
├── main.py                  # 入口: python -m llmchatflow [api]
├── config/
│   ├── config.py            # AppConfig dataclass + load_config()
│   └── config.yaml          # 默认配置
├── core/
│   ├── memory/              # 记忆智能层（检索、评分、策略）
│   ├── workflow/            # Pipeline Engine
│   ├── context/             # 上下文构建
│   ├── prompt/              # Prompt 组装与 Token 预算
│   ├── llm/                 # OpenAICompatibleClient
│   └── session/             # LocalSession
├── adapters/
│   ├── cli/                 # CLIAdapter
│   └── api/                 # APIAdapter
└── utils/                   # Embedding、FAISS、TokenCounter、Logging

apps/
└── api_server.py             # FastAPI HTTP 服务

examples/
├── cli_demo.py              # 交互式 CLI
├── library_demo.py          # 库用法
├── headless_demo.py         # 无 LLM 检索演示
└── api_client_demo.py       # HTTP 客户端

tests/                        # pytest 测试（123+ 用例）
data/                         # 运行时数据库目录（.gitignore 保护）
```

## Runtime Files

所有运行时产生的数据文件（SQLite `.db`、FAISS `.faiss`、日志）默认存放在 `data/` 目录下，通过 `.gitignore` 保护，不会污染工作区或误提交到 Git。

## Testing

```bash
# 快速测试（纯内存，约 60 秒）
pytest tests/ -m "not slow"

# 全部测试（包含 FAISS/SQLite 集成测试）
pytest tests/

# 带覆盖率报告
pytest tests/ -m "not slow" --cov=llmchatflow --cov-report=term-missing
```

## CI

GitHub Actions 在每次 push/PR 时自动运行快速测试（`pytest -m "not slow"`），要求覆盖率 ≥ 50%。

## API Endpoints

启动 API 服务器后：

| 端点 | 说明 |
|------|------|
| `GET /health` | 存活探针 |
| `GET /ready` | 就绪探针（检查 OPENAI_API_KEY） |
| `POST /chat` | 对话（需要 API Key） |
| `POST /retrieve` | 无头记忆检索（无需 API Key） |

## License

MIT
