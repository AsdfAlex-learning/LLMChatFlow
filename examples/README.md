# Examples

LLMChatFlow 使用示例。所有示例均已移除 `sys.path` hack，需要在 conda 环境中通过 `pip install -e .` 安装后运行。

## 前置条件

```bash
# 安装项目（可编辑模式）
pip install -e .

# 配置 API Key（创建 .env 文件）
cp .env.example .env
# 编辑 .env，设置 OPENAI_API_KEY 和 OPENAI_BASE_URL
```

## 示例列表

| 文件 | 用途 | 需要 API Key | 命令 |
|------|------|:---:|------|
| `cli_demo.py` | 交互式 CLI 对话 | ✅ | `python examples/cli_demo.py` |
| `library_demo.py` | 作为 Python 库导入使用 | ✅ | `python examples/library_demo.py` |
| `headless_demo.py` | 纯记忆检索（不调 LLM） | ❌ | `python examples/headless_demo.py` |
| `api_client_demo.py` | HTTP 客户端调用 API 服务 | ✅ | 需先启动 `python -m llmchatflow api` |

## 详细说明

### cli_demo.py — 交互式 CLI

最直观的演示方式，在终端中与 AI 对话。

```
Welcome to LLMChatFlow CLI Demo!
--------------------------------------------------
User: 你好
Assistant: 你好！有什么可以帮你的？
User: 我们刚才聊了什么？
Assistant: 你刚才和我打招呼，问有什么可以帮你。
```

每轮对话自动存储到记忆库，后续轮次能检索到之前的记忆。

### library_demo.py — 库调用

演示如何在自己的 Python 项目中嵌入 LLMChatFlow：

```python
from llmchatflow.config import load_config
from llmchatflow.core.workflow.engine import SemanticMemoryEngine
# ... 初始化 engine
response = engine.process("你好")
```

展示了最小初始化、会话创建、多轮对话流程。

### headless_demo.py — 纯检索

不调用 LLM，仅使用记忆智能层。演示 MemoryManager 的三个核心 API：

```python
manager = MemoryManager(store, embedder)
result = manager.retrieve("用户问题", session_id="...")   # 检索
view = manager.build_view(result, format="text")           # 格式化
manager.store(input, response, session_id="...")            # 存储
```

适用于已有 LLM 应用、只需复用记忆检索能力的场景。

### api_client_demo.py — HTTP 客户端

演示如何通过 HTTP API 调用 LLMChatFlow 服务：

1. 健康检查 `GET /health`
2. 单会话多轮对话 `POST /chat`
3. 空输入错误处理

运行前需启动 API 服务器：`python -m llmchatflow api`

## 常见问题

**Q: 运行报 `401 Authorization Required`？**
A: API Key 未配置。在项目根目录创建 `.env` 文件，设置 `OPENAI_API_KEY=sk-xxx`。

**Q: 首次运行下载模型很慢？**
A: CLI demo 和 library demo 首次运行会自动从 HuggingFace 下载 `BAAI/bge-small-zh-v1.5` 嵌入模型（~100MB），后续运行会使用缓存。headless demo 也需要此模型。

**Q: 如何清理运行时文件？**
A: 运行示例会产生 `*.db`、`*.faiss` 等文件，它们已在 `.gitignore` 中排除。手动删除即可：
```bash
rm *.db *.db-shm *.db-wal *.faiss
```
