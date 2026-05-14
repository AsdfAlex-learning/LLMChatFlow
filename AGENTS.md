# PROJECT KNOWLEDGE BASE

**Generated:** 2026-05-14
**Commit:** a1aeb46
**Branch:** main

## OVERVIEW
LLMChatFlow 是一个轻量级 AI 基础设施系统，管理"记忆 → 检索 → 上下文 → 推理"链。核心架构：Memory Intelligence Layer（MemoryPolicy + Retriever + ViewBuilder）+ Pipeline Workflow Engine。

## STRUCTURE
```
llmchatflow/
├── main.py                         # 入口: python -m llmchatflow [api]
├── config/                         # AppConfig dataclass (36 fields), YAML 加载
├── core/
│   ├── memory/                     # ⭐ 记忆智能层 — AGENTS.md 在此
│   │   ├── policy/                 #   MemoryPolicy ABC + DefaultMemoryPolicy
│   │   ├── manager.py              #   MemoryManager 统一入口
│   │   ├── retriever.py            #   FAISS+SQLite 检索编排
│   │   ├── view_builder.py         #   检索结果 → text/prompt/structured
│   │   ├── ranking.py              #   多因子评分 (temporal+similarity+importance)
│   │   ├── semantic.py             #   余弦相似度 fallback
│   │   ├── judge.py                #   LLM 记忆类型/重要性判定
│   │   └── storage.py              #   MemoryStore ABC
│   ├── workflow/                   # Pipeline Engine + SemantMemoryEngine
│   ├── context/                    # StructuredContextBuilder (4-block assembly)
│   ├── prompt/                     # StructuredPromptAssembler + token_budget
│   ├── llm/                        # OpenAICompatibleClient (sync+async)
│   └── session/                    # ISession ABC + LocalSession
├── adapters/
│   ├── cli/adapter.py              # CLIAdapter (input/output)
│   └── api/adapter.py              # APIAdapter (parse/format)
└── utils/                          # SentenceEmbedding, FaissIndex, TokenCounter
apps/
└── api_server.py                   # FastAPI server (POST /chat, lifespan singletons)
examples/
├── cli_demo.py                     # 交互式 CLI
├── library_demo.py                 # import llmchatflow 库用法
├── headless_demo.py                # 无 LLM 检索演示
└── api_client_demo.py              # HTTP 客户端演示
tests/                              # pytest, 50+ 测试
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| 理解检索管道 | `core/memory/retriever.py` | Embed→FAISS→Score→Select→Group |
| 修改评分逻辑 | `core/memory/ranking.py` | `compute_final_scores_by_type()` |
| 修改记忆选择策略 | `core/memory/policy/default.py` | `DefaultMemoryPolicy.select()` |
| 修改上下文组装 | `core/context/structured.py` | `build_messages()` |
| 修改 Token 预算 | `core/prompt/token_budget.py` | `trim_records_to_token_budget()` |
| 添加新记忆类型 | `core/memory/storage.py` (ABC) + `utils/sqlite_faiss_memory_store.py` (impl) |
| 运行完整工作流 | `core/workflow/engine.py` | `SemantMemoryEngine.process()` |
| Headless 检索 | `core/memory/manager.py` | `MemoryManager.retrieve()` |
| 配置系统 | `config/config.py` | `AppConfig` dataclass + `load_config()` |
| 测试参考 | `tests/` | pytest + MagicMock fixtures |

## CODE MAP

| Symbol | Type | Location | 职责 |
|--------|------|----------|------|
| `SemanticMemoryEngine` | class | `workflow/engine.py` | 对话编排，Full/Headless 双模式 |
| `MemoryManager` | class | `memory/manager.py` | 记忆统一入口: retrieve/store/build_view |
| `DefaultMemoryPolicy` | class | `memory/policy/default.py` | 桶选择 + 类型感知评分 |
| `MemoryRetriever` | class | `memory/retriever.py` | FAISS→SQLite→Policy 编排 |
| `MemoryViewBuilder` | class | `memory/view_builder.py` | 结果 → text/prompt/structured |
| `StructuredContextBuilder` | class | `context/structured.py` | 多源上下文(4 blocks) |
| `SQLiteFaissMemoryStore` | class | `utils/sqlite_faiss_memory_store.py` | SQLite+FAISS 线程安全 |
| `LLMJudge` | class | `memory/judge.py` | LLM 判定记忆类型+重要性 |
| `QueryRewriter` | class | `workflow/query_rewrite.py` | 查询重写(none/always/timed/count) |

## CONVENTIONS
- **ABC 定义接口**: 每个子系统提供 `base.py` 抽象基类（MemoryStore, LLMClient, ContextBuilder, PromptTemplate, ISession）
- **Config 驱动**: 所有参数化行为通过 `AppConfig` 单例读取，不硬编码
- **懒加载**: 顶层 `__init__.py` 和 `core/memory/__init__.py` 用 `__getattr__` 延迟导入 MemoryManager
- **Commit 风格**: `type(scope): description` — type=feat/fix/refactor/chore/test/docs, scope=模块名
- **Plan-driven**: 所有设计决策见 `plan.md`

## ANTI-PATTERNS (DO NOT)
- ❌ 在模块层导入 heavy ML 依赖（sentence_transformers, transformers, faiss）— 用懒加载
- ❌ 硬编码 memory_type/importance/scope/decay_rate — 用 config 或参数传入
- ❌ 绕过 MemoryStore ABC 直接操作 SQLite
- ❌ 平面单消息 prompt — 用 StructuredPromptAssembler 的结构化块
- ❌ `sys.path.insert()` hack — 依赖 pip install -e . 安装

## COMMANDS
```bash
# 安装 (conda)
./setup_conda.ps1

# 运行测试
pytest tests/ -v

# 运行 CLI 演示
python -m llmchatflow

# 启动 API 服务器
python -m llmchatflow api

# 分开运行示例
python examples/library_demo.py
python examples/headless_demo.py
```

## NOTES
- `plan.md` 是架构设计文档，Section 7 描述 Memory Intelligence Layer
- `CLAUDE.md` 为历史文档，AGENTS.md 为其更新版
- `.sisyphus/` 为 ultrawork 会话状态目录（已完成会话可清理）
- `_legacy/` 为旧 TelegramChatbot 代码，已 gitignore，与新系统无关
- FAISS 索引文件 `*.faiss` + SQLite WAL 文件 `*.db-shm` / `*.db-wal` 已 gitignore
