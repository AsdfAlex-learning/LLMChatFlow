# LLMChatFlow 重构架构设计文档

## 1. 核心目标
构建一个基于 **Structured Memory + Hybrid Retrieval + Context Orchestration** 的轻量级 LLM Chat Infra。

一句话定义：
**LLMChatFlow 是一个用于管理“记忆 → 检索 → 上下文 → 推理”的轻量级 AI Infra 系统。**

本次重构聚焦三条主线：
1.  **Memory System（结构化 + 分层）**
    - 记忆类型：`episodic / habit / summary`
    - 作用域：`user / session`
    - 关键属性：`importance / time_decay`
2.  **Retrieval Pipeline（核心能力）**
    - FAISS semantic recall
    - type-aware scoring
    - bucket-based selection
    - turn-level reconstruction
3.  **Context Orchestration（关键能力）**
    - memory selection → context structuring
    - token-aware prompt 构建
    - multi-source context 融合

**明确不做**：
- LangChain 集成
- 复杂 Agent 逻辑
- 自动总结/反思（避免工程复杂度爆炸）

---

## 2. 系统逻辑与分层架构
### 核心逻辑流
```mermaid
graph TD
    UI[User Input] --> QR[Query Rewrite]
    QR --> Emb[Embedding]
    Emb --> VS[Vector Search (FAISS)]
    VS --> MR[Memory Ranking]
    MR --> CC[Context Construction]
    CC --> LLM[LLM Response]
    LLM --> MS[Memory Storage]
```

### 四层架构体系
1.  **Application Layer**: `core/workflow/engine` (对话编排)
2.  **AI Layer**: `utils/embedding` / `core/llm` (模型服务)
3.  **Retrieval Layer**: `utils/faiss_helper` (向量索引)
4.  **Storage Layer**: `utils/sqlite_faiss_memory_store` (元数据 + 向量存储)

---

## 3. 项目目录结构
```
LLMChatFlow/
│
├── llmchatflow/                        # 主包
│   ├── main.py                         # 程序入口（库内）
│   ├── adapters/
│   │   ├── cli/
│   │   │   └── adapter.py              # CLI 适配层
│   │   └── api/
│   │       └── adapter.py              # API 适配层（请求/响应映射）
│   ├── config/
│   │   ├── config.py                   # 配置定义与加载
│   │   └── config.yaml                 # 默认配置文件
│   ├── core/
│   │   ├── context/                    # 上下文构建
│   │   ├── llm/                        # LLM 抽象与实现
│   │   ├── memory/                     # 记忆管理、语义检索、重排
│   │   ├── prompt/                     # Prompt 组装与 token 预算
│   │   ├── session/                    # 会话状态管理
│   │   └── workflow/
│   │       └── engine.py               # 对话工作流编排
│   └── utils/
│       ├── embedding.py                # 向量工具
│       ├── faiss_helper.py             # FAISS 索引封装
│       ├── sqlite_faiss_memory_store.py# SQLite + FAISS 记忆存储
│       ├── token_counter.py            # Token 计数
│       └── logging_utils.py            # Logging 配置
│
├── examples/
│   ├── cli_demo.py                     # Demo / 用例：本地 CLI 对话演示
│   ├── library_demo.py                 # Demo / 用例：作为 Python Library 集成调用
│   └── api_client_demo.py              # Demo / 用例：通过 HTTP API 调用服务
│
├── apps/
│   └── api_server.py                   # API 封装入口（对外 HTTP 服务）
│
├── setup_conda.ps1                     # Conda 一键环境初始化（Windows）
├── setup_conda.sh                      # Conda 一键环境初始化（Linux/macOS）
├── setup_venv.ps1                      # venv 一键环境初始化（Windows）
├── setup_venv.sh                       # venv 一键环境初始化（Linux/macOS）
│
├── requirements.txt                    # 运行依赖
├── pyproject.toml                      # 包构建与项目元信息
├── .env.example                        # 环境变量模板
├── README.md                           # 使用说明
└── plan.md                             # 架构与实施计划
```

### 3.1 Demo 与 API 封装用例（新增）
1. **Library 用例（`examples/library_demo.py`）**
   - 场景：业务项目中通过 `import llmchatflow` 方式直接嵌入。
   - 目标：演示最小初始化参数、会话创建、一次请求处理流程。
2. **API 封装（`apps/api_server.py` + `llmchatflow/adapters/api/adapter.py`）**
   - 场景：将 LLMChatFlow 封装为统一 HTTP 服务，供前端或其他后端调用。
   - 目标：隔离协议层与核心流程，统一请求校验、错误转换与响应结构。
3. **API 调用用例（`examples/api_client_demo.py`）**
   - 场景：客户端通过 HTTP 请求调用 API 服务。
   - 目标：演示 `POST /chat` 的请求参数、响应解析与异常处理路径。

---

## 4. 核心模块设计详解

### 4.1 Chat Engine (对话核心)
- **文件**: `core/workflow/engine.py`
- **职责**: 整个对话流程的 Orchestrator，基于 Pipeline 模式编排 Embedding → Retrieval → LLM → Storage 四阶段处理。
- **伪代码**:
  ```python
  def chat(user_input):
      rewritten_query = rewrite(user_input)
      memories = memory_manager.retrieve(rewritten_query)
      ranked_memories = memory_ranker.rank(memories)
      context = context_builder.build(ranked_memories)
      response = llm.generate(context)
      memory_manager.store(user_input, response)
      return response
  ```

### 4.2 Embedding Module
- **文件**: `utils/embedding.py`
- **模型**: `BAAI/bge-small-zh-v1.5`
- **职责**: 文本 -> 向量 (Float32, Normalized)，基于 SentenceTransformer 封装，线程安全 embed，自动检测维度，含 cosine_similarity 工具函数。
- **设计原则**: 独立模块，未来可替换模型。

### 4.3 Vector Store (FAISS)
- **文件**: `utils/faiss_helper.py`
- **职责**: 向量索引管理 (Add, Search, Load, Save, Reset)，封装 `FaissIndex` 类，支持 IndexFlatIP + IndexIDMap2，提供 L2 归一化、原子化保存（tmp → rename）、懒加载 FAISS 库。
- **实现**: 使用 `faiss.IndexFlatIP` (Inner Product) + `IndexIDMap2` 实现向量与 UUID 映射。

### 4.4 SQLite + FAISS Memory Storage
- **文件**: `utils/sqlite_faiss_memory_store.py`
- **职责**: 统一的 SQLite + FAISS 组合存储，管理记忆元数据、会话、参与者关系及向量索引。支持异步 FAISS 批量写入、脏标记追踪与索引重建，线程安全。
- **关键方法**: `insert_memory()`、`insert_message()`、`fetch_messages_by_session()`、`fetch_memories_by_uuids()`、`search_records()`、`rebuild_faiss()`。

#### 4.4.1 数据表清单（Tables）

**表 1：`memory` 表（记忆核心表）**
- **用途**：承载对话记录与长期记忆的核心数据表，整合对话轮次、记忆分类、权重计算等核心能力。

| 字段名 | 数据类型 | 描述 |
| :--- | :--- | :--- |
| `uuid` | TEXT | 主键，唯一标识每条记忆记录 |
| `turn_id` | TEXT | 关键字段，标记该条记忆所属的LLM调用轮次，用于群聊、流式对话、回放调试 |
| `user_id` | TEXT | 记忆所属用户，标记记忆的归属人 |
| `session_id` | TEXT | 记忆所属会话，标记记忆的会话维度 |
| `role` | TEXT | 消息角色类型，分为 `user`（用户）、`assistant`（AI助手）、`system`（系统，预留） |
| `content` | TEXT | 自然语言文本，存储最终完整的对话内容（非流式片段） |
| `memory_type` | TEXT | 记忆类型，分为 `episodic`（对话片段）、`habit`（用户偏好）、`summary`（压缩记忆）、`system`（系统生成） |
| `memory_scope` | TEXT | 记忆作用范围，保留两种明确维度：`user`（用户全局记忆，跨会话）、`session`（当前会话记忆） |
| `importance` | INTEGER | 整数权重值，可由LLM或规则生成，用于衡量记忆重要程度 |
| `decay_rate` | REAL | 时间衰减系数，用于计算记忆时效性权重，支持不同记忆配置不同衰减速度 |
| `timestamp` | INTEGER | 记忆创建的时间戳 |
| `metadata` | TEXT | JSON格式扩展字段，存储额外信息，例如 `{"source":"chat","confidence":0.82,"extracted":true}` |

**表 2：`session` 表（会话管理表）**
- **用途**：管理对话会话全生命周期的基础表，新增记忆检索策略配置能力。

| 字段名 | 数据类型 | 描述 |
| :--- | :--- | :--- |
| `session_id` | TEXT | 主键，唯一标识每个会话 |
| `owner_id` | TEXT | 会话创建者ID，标记会话归属 |
| `timestamp` | INTEGER | 会话创建时间戳 |
| `mode` | TEXT | 会话用途类型，如 `chat`, `isolated`, `assistant`, `companion`, `group` |
| `memory_policy` | TEXT | 关键字段，JSON格式存储检索策略，如 `{"retrieval_mode":"filter_first","top_k":20}` |
| `metadata` | TEXT | 预留扩展字段，存储会话额外配置信息 |

**表 3：`session_participants` 表（会话参与者表）**
- **用途**：维护会话与参与者多对多关系的关联表，支持多角色协作。

| 字段名 | 数据类型 | 描述 |
| :--- | :--- | :--- |
| `uuid` | TEXT | 独立主键，标识本条关联记录 |
| `session_id` | TEXT | 外键，关联`session`表主键，标记所属会话 |
| `participant_id` | TEXT | 参与者ID，可对应用户或AI账号 |
| `role` | TEXT | 参与者角色类型，分为 `user`, `assistant`, `system` |

---

### 4.5 FAISS（向量索引）
- **职责**：直接在 FAISS 中构建向量索引，实现记忆的语义检索，无需单独创建 SQLite 映射表。
- **结构映射**：
  - **`id`**：与 `memory` 表的 `uuid` 完全一致（如需要整数ID可内部映射或使用特定FAISS索引），实现向量与记录一一映射。
  - **`vector`**：由 `content` 字段文本向量化生成的向量数据。

---

### 4.6 核心运行机制

#### 1️⃣ Turn 生成机制
每次 LLM 调用对应一个唯一的 `turn_id`（通过 UUID 生成）。用户输入的所有消息和 AI 输出的回复都绑定同一个 `turn_id`，以此实现对话轮次的精准标记，支撑群聊、流式对话、会话回放与调试等能力。

#### 2️⃣ Retrieval 检索策略
检索策略配置在 `session` 表的 `memory_policy` 字段中，包含两种核心模式：
- **Filter First 模式**：先通过 SQLite 筛选 `user_id`/`session_id` 匹配的记忆记录，再对筛选结果进行 FAISS 语义检索。
- **Recall First 模式（备用）**：先全局调用 FAISS 召回相似记忆，再基于 `user_id`/`session_id` 过滤结果。

#### 3️⃣ Memory 打分机制
记忆最终排序分数由三部分加权计算得出：
`final_score = similarity + importance_weight + time_decay`
其中 `time_decay`（时间衰减值）通过公式 `exp(decay_rate * delta_time)` 计算。不同记忆可配置不同 `decay_rate`，实现差异化的时效性衰减。

#### 4️⃣ Context Builder 上下文构建机制
作为系统核心模块，输入为用户当前输入内容 + 检索到的记忆数据，输出为供 LLM 调用的完整 prompt。该模块需精准控制三部分内容：
1. 按 `turn_id` 拼接的近期对话消息。
2. 按 `final_score` 排序后的 TopK 记忆注入。
3. 记忆摘要的合理插入。
确保 prompt 的完整性与精简性。

#### 5️⃣ Memory 写入策略
并非所有对话内容都写入记忆表，需按类型区分：
- **episodic**: 用户对话内容 / AI助手回复。
- **habit**: 用户偏好信息。
- **summary**: 长对话压缩内容。
写入规则可基于预设规则实现，也可通过 LLM 判断是否写入，避免无效记忆冗余存储。

#### 6️⃣ 核心流程异常处理规则

各核心环节在运行时可能遭遇失败，需按以下规则进行降级、重试与兜底，确保系统在任何单点故障下仍可产出可用结果。

**规则 1：Embedding 失败降级**
- **触发条件**：`utils/embedding.py` 的 `embed()` 调用抛出异常或返回零向量。
- **处理流程**：
  1. 立即重试 1 次（同一输入，间隔 0ms）。
  2. 重试仍失败 → 降级为原始文本检索：跳过 FAISS 向量搜索，直接调用 `SQLiteFaissMemoryStore.fetch_messages_by_session()` 获取近期记忆，再由 `core/memory/semantic.py` 的 `semantic_scores()` 做余弦相似度兜底评分。
  3. 无论降级与否，均输出 `WARNING` 级别日志，内容包含 `session_id`、`user_id`、异常信息、是否降级成功。
- **实现位置**：`core/context/structured.py` 的 `build_messages()` 方法内，FAISS search 分支的 `except` 块。

**规则 2：FAISS 索引缺失自动恢复**
- **触发条件**：`utils/faiss_helper.py` 的 `FaissIndex` 加载失败（文件不存在、损坏、或 FAISS 库不可用），`store._faiss` 为 `None`。
- **处理流程**：
  1. 自动初始化空 `FaissIndex`（维度从 SQLite `kv` 表读取 `embedding_dim`，若无则从首次写入的向量推断）。
  2. 在后台线程异步执行 `rebuild_faiss()`，从 SQLite `faiss_vectors` 表批量加载历史向量重建索引，期间搜索请求走规则 1 的降级路径。
  3. 重建完成后，后续搜索请求自动切回 FAISS 向量检索。
  4. 输出 `WARNING` 日志：FAISS 不可用原因、是否触发重建、重建记录数。
- **实现位置**：`utils/sqlite_faiss_memory_store.py` 的 `_ensure_faiss()` 方法。

**规则 3：SQLite 写入失败兜底**
- **触发条件**：`utils/sqlite_faiss_memory_store.py` 的 `insert_memory()` / `insert_message()` 执行 SQL 时抛出异常。
- **处理流程**：
  1. 立即重试 2 次，每次间隔 100ms（应对短暂锁竞争或磁盘 IO 抖动）。
  2. 3 次全部失败 → 将待写入数据序列化为 JSON，追加写入临时文件（路径：`{storage_path}/pending_writes.jsonl`），每行一条待写入记录。
  3. 启动后台异步重试线程，定期（每 30 秒）读取临时文件，逐条重新尝试写入 SQLite，写入成功后从文件中移除该行。
  4. 临时文件写入本身失败 → 输出 `ERROR` 日志，包含完整待写入数据，由运维介入处理。
- **实现位置**：`utils/sqlite_faiss_memory_store.py` 的 `insert_memory()` 和 `insert_message()` 方法。

**规则 4：Token 超限分级裁剪**
- **触发条件**：组装后的 prompt token 数超过 `context_max_token`。
- **处理流程**（按优先级依次执行，每步后重新计算 token 数，达标即停）：
  1. **优先裁剪低评分记忆**：按 `final_score` 升序，逐条移除检索到的记忆记录，直到 token 数 ≤ `context_max_token`。
  2. **压缩对话历史**：若记忆全部移除后仍超限，对对话历史按时间窗口压缩——保留最近 N 轮原文，更早的轮次用 `summary` 类型记忆替代（若存在）或直接截断。
  3. **保证 min_token 下限**：若经上述裁剪后 token 数 < `context_min_token`，则至少保留：当前用户输入（完整）+ 系统提示词（完整）+ 1 条最高评分记忆（如有），确保 LLM 始终获得最小可用上下文。
  4. 每次触发裁剪时输出 `INFO` 日志：裁剪阶段、移除条数、最终 token 数。
- **实现位置**：`core/prompt/token_budget.py` 的 `trim_records_to_token_budget()` 函数，需扩展为多阶段裁剪逻辑。

**异常处理总原则**：
- **永不静默失败**：所有降级和兜底操作必须记录日志，包含足够的上下文信息用于事后排查。
- **降级优于报错**：系统在单点故障下应尽可能产出可用结果，而非直接抛出异常中断请求。
- **数据不丢失**：写入失败时必须通过临时文件等机制确保数据可恢复，避免记忆静默丢失。

---

## 5. 核心配置清单 (Configuration)

| 模块 | 配置项名 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| **基础配置** | `user_mode` | `single` | 单/多用户模式 (single/multi) |
| **基础配置** | `session_id_default` | `default_session` | 单用户默认 session_id |
| **查询重写** | `query_rewrite_trigger` | `none` | 触发方式 (none/always/timed/count) |
| **查询重写** | `query_rewrite_persist` | `none` | 落库方式 (none/memories_metadata) |
| **Embedding** | `embedding_input_source` | `original` | 输入来源 (rewritten 优先 / original 固定) |
| **Embedding** | `embedding_dimension` | `384` | 向量维度 |
| **Embedding** | `embedding_model` | `BAAI/bge-small-zh-v1.5` | Embedding 模型（HuggingFace repo 或本地路径） |
| **Embedding** | `embedding_device` | `` | 设备选择（`cpu`/`cuda`/`mps`，空为自动） |
| **FAISS** | `faiss_topk` | `20` | 候选召回数 |
| **FAISS** | `faiss_filter_strategy` | `global` | 过滤策略 (global/session_based) |
| **评分重排** | `ranking_score_normalize` | `True` | 分值是否归一化 |
| **评分重排** | `ranking_weight_mode` | `by_memory_type` | 权重模式 (global/by_memory_type) |
| **评分重排** | `ranking_type_weights_episodic` | `{"alpha":0.5,"beta":0.1,"theta":0.4}` | episodic 权重（similarity/importance/time_decay） |
| **评分重排** | `ranking_type_weights_habit` | `{"alpha":0.7,"beta":0.3,"theta":0.0}` | habit 权重（similarity/importance/time_decay） |
| **评分重排** | `ranking_type_weights_summary` | `{"alpha":0.6,"beta":0.3,"theta":0.1}` | summary 权重（similarity/importance/time_decay） |
| **评分重排** | `ranking_type_weights_default` | `{"alpha":0.5,"beta":0.2,"theta":0.3}` | 未知类型兜底权重 |
| **评分重排** | `ranking_keep_count` | `10` | 基础保留条数 |
| **上下文** | `context_max_token` | `2000` | 总 Token 上限 |
| **上下文** | `context_min_token` | `500` | 强制 Token 下限 |
| **上下文** | `history_summarize` | `True` | 是否开启对话历史总结 |
| **上下文** | `system_prompt` | `built-in` | 系统提示词 |
| **记忆存储** | `memory_type_llm_judge` | `True` | LLM 自动判断记忆类型 |
| **记忆存储** | `faiss_write_strategy` | `real_time` | 向量写入策略 (real_time/batch) |
| **记忆存储** | `importance_llm_judge` | `True` | LLM 自动评分重要性 |
| **记忆存储** | `importance_default` | `0.5` | 评分失败兜底值 |
| **归档规则** | `archive_days` | `90` | 归档天数阈值 |
| **归档规则** | `archive_importance` | `0.2` | 归档重要性阈值 |
| **Logging** | `logging_level` | `INFO` | 日志层级 (DEBUG/INFO/WARNING/ERROR) |
| **Logging** | `logging_console` | `True` | 是否启用控制台日志记录 |
| **Logging** | `logging_file_path` | `` | 日志文件路径（空表示禁用） |
| **Logging** | `logging_json` | `False` | 是否输出 JSON 格式日志 |

### 5.1 配置分层策略（库内部完整 + 外部精简）
- **内部配置层（Full Config）**：保留完整配置项，用于覆盖检索、重排、上下文构建、记忆写入、归档等全部链路能力，作为框架内部统一运行基线。
- **外部配置层（Public Config）**：对库使用者默认只暴露最小必要配置，其他参数采用内部默认值，避免接入阶段配置负担过高。
- **覆盖规则**：外部显式传入 > 业务初始化参数 > 内部默认值；未传入项自动回落到内部默认配置。
- **兼容目标**：保证“开箱可用”与“深度可调”同时成立，既支持最小接入，也支持后续按需逐项放开高级配置。

### 5.2 Python Library 使用场景下的外部手动配置
- **使用方式**：库使用者通过 `import` 引入配置对象，在应用启动阶段手动设置外部配置项。
- **外部必配项（最小集）**：`llm_provider`、`llm_model`、`api_key`、`embedding_model`、`storage_path`。
- **外部建议可配项**：`session_id_default`、`context_max_token`、`faiss_topk`、`system_prompt`。
- **高级配置开放策略**：默认不要求业务侧配置 `ranking_type_weights_*`、`archive_days`、`faiss_write_strategy` 等高级参数，仅在业务明确需要时手动覆盖。
- **交付约束**：库层不强制业务侧提供完整配置清单；业务侧仅对自身场景负责手动配置必要项，其余由库内部托管。

### 5.3 日志记录（英文记录）
目标：
- 实现无需添加打印语句即可进行调试和生产监控。
- 在需要时保持日志输出的一致性和机器可解析性。
- 避免泄露机密信息或大型负载（嵌入式内容、API 密钥、完整提示）。
默认行为：
- 启用控制台日志记录，级别为“INFO”。
- 可选的文件日志记录，通过 `logging_file_path` 进行配置。
- 可选的 JSON 格式日志记录，通过 `logging_json` 用于日志管道的摄取。
推荐的日志字段（如有）：
- `会话 ID`、`轮次 ID`、`用户 ID`
- `组件`（例如，工作流、上下文、存储、检索）
- `延迟（毫秒）`
- `输入项`、`输出项`（例如，候选项、排序项、选定项）

---

## 6. 核心工作流 (Pipelines)

### 6.1 Memory Retrieval Pipeline
1.  **User Query**
    - 输入：`user_input: str`
    - 会话：`session_id: str` (默认 `default_session`，可配 `user_mode`)
2.  **Rewrite Query（可选）**
    - 触发条件：`query_rewrite_trigger` (none/always/timed/count)
    - 输出：`rewritten_query: str`
    - 是否落库：`query_rewrite_persist` (none/memories_metadata)
3.  **Embedding（Query Vector）**
    - 输入：`rewritten_query` 或 `user_input` (配置 `embedding_input_source`)
    - 输出：`query_vector: float[]` (维度 `embedding_dimension`: 384)
4.  **FAISS TopK Search（候选召回）**
    - 输入：`query_vector`、`top_k: int` (配置 `faiss_topk`: 20)
    - 输出：`candidate_ids: list[str]`
    - 过滤策略：`faiss_filter_strategy` (global/session_based)
5.  **Load Metadata (SQLite)（按 ID 批量取回）**
    - 读取表：`memories`
    - 查询条件：`id IN (candidate_ids)`
    - 输出：`candidate_memories: list[Memory]`
6.  **Memory Ranking（重排）**
    - 输入：`candidate_memories`
    - 评分公式：`final_score = alpha * similarity + beta * importance + theta * time_decay`
    - 权重来源：根据 `memory_type` 动态选择 `ranking_type_weights_*`
        - `episodic`: `alpha=0.5, beta=0.1, theta=0.4`
        - `habit`: `alpha=0.7, beta=0.3, theta=0.0`
        - `summary`: `alpha=0.6, beta=0.3, theta=0.1`
    - 是否归一化：`ranking_score_normalize` (True)
    - 输出：`ranked_memories: list[Memory]` (保留 `ranking_keep_count`: 10)
7.  **Context Construction（上下文构建）**
    - 输入：`ranked_memories` + 对话历史
    - Token Budget 策略：`context_max_token` (2000) - `context_min_token` (500)
    - 历史总结：`history_summarize` (True)
    - 输出：`messages/prompt`

### 6.2 Memory Storage Pipeline
1.  **Conversation**
    - 输入：`user_input`、`llm_response`
    - 会话：`session_id`
2.  **Memory Extraction（生成记忆对象）**
    - 规则：抽取 user 和 assistant 消息
    - 类型判断：`memory_type_llm_judge` (True) -> LLM 决定 habit/episodic/summary
    - 输出：`memories_to_store: list[Memory]`
3.  **Importance Scoring（重要性赋值）**
    - 策略：`importance_llm_judge` (True) -> LLM 打分
    - 兜底：`importance_default` (0.5)
4.  **Embedding（Content Vector）**
    - 输入：Memory.content
    - 输出：Memory.embedding (归一化)
5.  **FAISS Add（写入向量索引）**
    - 写入键：Memory.id
    - 策略：`faiss_write_strategy` (real_time/batch)
    - 失败补偿：标记待重建 (Dirty Flag in SQLite)
6.  **SQLite Insert（写入元数据）**
    - 写入表：`memories`
    - 写入顺序：先 SQLite 后 FAISS (确保元数据安全)
    - 冲突策略：忽略 (Ignore) 或 覆盖 (Replace)

---

## 7. 产品化能力升级：Memory Intelligence Layer

### 7.1 核心判断
当前阶段的关键任务不是继续堆叠功能，而是抽象出独立的 **Memory Intelligence Layer**。  
目标是让系统从“存储 + 检索组件集合”升级为“可直接输出高质量记忆选择结果的决策系统”。

### 7.2 双模式定义（必须并行支持）
1. **Full Mode（端到端模式）**
   - 流程：`User -> LLMChatFlow -> Response`
   - 价值：提供完整对话编排与推理链路。
2. **Headless Mode（无头记忆模式）**
   - 流程：`User App -> LLMChatFlow(memory only) -> memories/context`
   - 价值：让已有应用仅复用记忆智能层，不绑定完整聊天流程。

### 7.3 产品化目标
- 用户不需要先理解或重写评分公式即可获得可用结果。
- 默认策略覆盖 80% 常见场景，支持开箱即用。
- 高级用户可覆盖策略，但不是使用门槛。

### 7.4 关键抽象：MemoryPolicy
```python
class MemoryPolicy:
    def score(memory, query) -> float: ...
    def select(memories) -> list: ...
```

设计原则：
- **默认策略优先**：`DefaultMemoryPolicy` 作为系统默认入口。
- **可覆盖扩展**：允许通过 `CustomPolicy` 注入自定义策略。
- **接口稳定**：对业务暴露一致的 retrieve API。

### 7.5 Headless API 设计
默认调用：
```python
memories = memory_manager.retrieve(
    query="用户输入",
    user_id="xxx",
    session_id="xxx",
)
```

高级调用：
```python
memories = memory_manager.retrieve(
    query,
    policy=CustomPolicy(),
)
```

约定：
- 未传入 `policy` 时，自动使用 `DefaultMemoryPolicy`。

### 7.6 DefaultMemoryPolicy 内部职责
默认策略至少应封装以下流程：
1. FAISS recall
2. type-aware scoring
3. bucket-based selection
4. turn-level reconstruction

对外表现为：
- 输入 query
- 输出高质量 memories/context

### 7.7 目录结构调整建议
在 `core/memory/` 下新增策略层与检索层，与 Section 3 目录结构对齐：
```text
core/memory/
  base.py              # MemoryRetriever ABC（已有）
  ranking.py           # 评分函数（已有）
  semantic.py          # 语义相似度（已有）
  storage.py           # MemoryStore ABC（已有）
  manager.py           # 新增：MemoryManager 统一入口
  retriever.py         # 新增：检索编排（FAISS + SQLite + Ranking）
  view_builder.py      # 新增：Memory View 表现层
  policy/
    __init__.py
    base.py            # 新增：MemoryPolicy ABC
    default.py         # 新增：DefaultMemoryPolicy
```

### 7.8 实施优先级
第一优先级：实现可落地版本 `DefaultMemoryPolicy`，要求：
- 不需要额外配置即可运行
- 输出稳定且可解释
- 覆盖大多数真实检索场景

### 7.9 Headless Mode 持久化边界与 Memory View
#### 7.9.1 默认持久化原则
- Headless Mode 返回的检索结果与格式化片段默认 **不落库**。
- 仅持久化原始 memory 元数据与向量，不持久化 query 下的派生视图。

原因：
- 返回内容属于 derived data，生命周期短且强依赖当前上下文。
- 持久化派生视图会导致 I/O 增长、数据冗余与格式版本不一致。

#### 7.9.2 核心抽象：Memory View
定义：
- **Memory View = memory 在当前 query 下的临时表达**。

设计约束：
- 动态生成，不作为长期存储对象。
- 可按下游用途输出不同格式（text / prompt / structured）。

#### 7.9.3 分层拆分（Retrieval 与 View 解耦）
1. **Memory Retrieval（数据层）**
   - 输入：query/user_id/session_id
   - 输出：`Memory` / `Turn` 结构化结果
2. **Memory View Builder（表现层）**
   - 输入：retrieval 结果
   - 输出：文本视图、prompt 片段或结构化视图

#### 7.9.4 Headless 返回约定
方案 A（默认）：
```python
result = memory_manager.retrieve(...)
{
    "memories": [...],
    "turns": [...],
}
```

方案 B（可选）：
```python
view = memory_manager.build_view(memories)
```

约定：
- 默认返回结构化数据，不强制返回最终 prompt。
- 需要 prompt 时由 `build_view()` 显式生成。

#### 7.9.5 缓存策略边界
推荐缓存：
1. Query-level retrieval cache（`query + user_id + session_id`）
2. embedding cache（`query -> embedding`）

不推荐缓存：
- 最终 prompt 字符串（格式强相关，复用价值低且易失效）。

#### 7.9.6 API 形态统一
1. Headless Retrieval API
```python
memories = memory_manager.retrieve(query, user_id, session_id)
```
2. View Builder API
```python
view = memory_manager.build_view(memories)
```
3. Full Pipeline API
```python
response = chatflow.run(...)
```

#### 7.9.7 模块落地建议
在 `core/memory/` 下新增，与 Section 7.7 目录结构对齐：
```text
core/memory/
  retriever.py         # Memory Retrieval（数据层）
  view_builder.py      # Memory View Builder（表现层）
```

交付要求：
- `retriever.py` 中的 `retrieve()` 专注高质量结构化召回
- `view_builder.py` 中的 `build_view()` 负责可控格式化与 token 约束

---

## 8. 测试与验证标准

### 8.1 单元测试

覆盖核心算法、存储、检索三大模块，目标覆盖率 ≥ 80%。

#### 8.1.1 核心算法测试（`core/memory/ranking.py`、`core/memory/semantic.py`、`core/prompt/token_budget.py`）

| 测试项 | 测试文件 | 验证内容 |
| :--- | :--- | :--- |
| `temporal_score()` | `tests/test_ranking.py` | 时间衰减计算正确性：`exp(-lam * delta_days)`，边界值（delta=0 → 1.0，极大 delta → ≈0.0） |
| `recency_scores()` | `tests/test_ranking.py` | 排名递减分值：第1条=1.0，第6条及以后=0.1，空列表返回空 |
| `compute_final_scores()` | `tests/test_ranking.py` | 4因子加权计算：`alpha*sim + beta*imp + gamma*decay + delta*recency`，输入长度不匹配时抛异常 |
| `compute_final_scores_by_type()` | `tests/test_ranking.py` | 按记忆类型选择权重、归一化/非归一化输出、未知类型走 default_weights、所有类型全覆盖 |
| `semantic_scores()` | `tests/test_semantic.py` | 余弦相似度计算精度、零向量返回 0.0、维度不匹配返回 0.0 |
| `within_budget()` | `tests/test_token_budget.py` | Token 数在预算内/外判定、空文本列表 |
| `trim_records_to_token_budget()` | `tests/test_token_budget.py` | 优先移除最低分记录、裁剪后 token 数 ≤ max_tokens、空列表/单条记录边界 |

#### 8.1.2 存储测试（`utils/sqlite_faiss_memory_store.py`、`utils/faiss_helper.py`）

| 测试项 | 测试文件 | 验证内容 |
| :--- | :--- | :--- |
| `FaissIndex` 创建与搜索 | `tests/test_faiss_helper.py` | IndexFlatIP + IndexIDMap2 初始化、add + search 向量召回正确、L2 归一化验证、save + load 持久化往返 |
| `FaissIndex` 边界 | `tests/test_faiss_helper.py` | 空索引搜索返回空、ntotal 计数、reset 清空 |
| `insert_memory()` | `tests/test_sqlite_faiss_store.py` | 写入后可通过 `fetch_memories_by_uuids()` 读回、字段完整性（uuid/turn_id/role/content/importance/memory_type/timestamp） |
| `insert_message()` | `tests/test_sqlite_faiss_store.py` | 写入后可通过 `fetch_messages_by_session()` 读回、多消息顺序正确 |
| `search_records()` | `tests/test_sqlite_faiss_store.py` | `global` 策略：不按 session 过滤；`session_based` 策略：仅返回目标 session 记忆；TopK 截断正确性 |
| `rebuild_faiss()` | `tests/test_sqlite_faiss_store.py` | 重建后 FAISS 向量数与 SQLite `faiss_vectors` 表行数一致、搜索结果可召回 |
| Schema 完整性 | `tests/test_sqlite_faiss_store.py` | 验证 `memory`/`session`/`session_participants`/`faiss_vectors`/`kv`/`faiss_kv` 六张表均存在、字段类型正确 |

#### 8.1.3 检索测试（`core/context/structured.py`、`utils/embedding.py`）

| 测试项 | 测试文件 | 验证内容 |
| :--- | :--- | :--- |
| `StructuredContextBuilder.build_messages()` | `tests/test_context_structured.py` | 返回 messages 列表、FAISS 搜索成功路径与降级路径均产出结果、token 裁剪生效 |
| `SentenceEmbedding.embed()` | `tests/test_embedding.py` | 输出向量维度正确、归一化后 L2 范数 ≈ 1.0、空文本返回零向量、模型加载失败返回零向量 + 警告日志 |
| `cosine_similarity()` | `tests/test_embedding.py` | 相同向量 → 1.0、正交向量 → 0.0、零向量 → 0.0 |

### 8.2 端到端测试场景

模拟真实使用链路，验证从用户输入到 LLM 调用（可 mock）的完整流程。

#### 8.2.1 场景 1：单用户短会话

- **描述**：1 个用户、1 个 session、3-5 轮对话。
- **验证点**：
  1. 每轮对话后，`memory` 表新增 2 条记录（user + assistant），`turn_id` 相同。
  2. 第 3 轮起，`build_messages()` 返回的 prompt 中包含前序轮次的检索记忆。
  3. 记忆评分按 `by_memory_type` 权重计算，结果稳定可复现。
  4. 存储的 `memory_type` 正确（至少有 `episodic` 类型记录产生）。
- **测试文件**：`tests/test_e2e_short_session.py`

#### 8.2.2 场景 2：多用户会话

- **描述**：2 个用户、3 个 session（含 1 个共享 session），各 3 轮对话。
- **验证点**：
  1. `session_participants` 表正确维护多对多关系。
  2. `session_based` 过滤策略下，检索结果仅包含当前 session 的记忆，不泄漏其他 session 数据。
  3. `global` 过滤策略下，检索结果可包含跨 session 但同 user 的记忆。
  4. 不同用户的记忆按 `user_id` 隔离，`fetch_messages_by_session()` 不返回非本 session 记录。
- **测试文件**：`tests/test_e2e_multi_user.py`

#### 8.2.3 场景 3：长会话（≥50 轮）

- **描述**：1 个用户、1 个 session、50 轮对话，每轮含 1-2 条用户消息。
- **验证点**：
  1. Token 控制生效：`build_messages()` 返回的 prompt token 数 ≤ `context_max_token`（差值 ≤ 10%）。
  2. 对话历史裁剪优先移除低评分记忆，高评分记忆保留。
  3. `history_summarize` 开启时，较早轮次的记忆被标记为 `summary` 类型或通过总结机制压缩（若已实现；未实现时验证裁剪降级路径）。
  4. `faiss_topk=20` 限制下，检索返回的记忆条数不超过 TopK 值。
  5. 全程无异常抛出，FAISS 索引和 SQLite 数据一致。
- **测试文件**：`tests/test_e2e_long_session.py`

### 8.3 性能指标

系统在常规硬件（CPU: 4 核 / RAM: 8GB / SSD）下需满足以下指标：

| 指标 | 基准值 | 测量方法 | 测试文件 |
| :--- | :--- | :--- | :--- |
| **检索延迟** | ≤ 200ms（Top20 召回） | 从 `search_records()` 调用到返回结果的 wall-clock 时间，取 100 次平均值。前提：FAISS 索引已加载到内存，记忆总量 ≤ 10,000 条。 | `tests/test_perf_retrieval.py` |
| **Token 控制精度** | 实际 prompt token 数与 `context_max_token` 差值 ≤ 10% | 构造超限场景（输入记忆 token 总和 > `context_max_token` × 2），调用 `build_messages()` 后对返回的 prompt 做 token 计数，计算 `(actual - max_token) / max_token`。 | `tests/test_perf_token_control.py` |
| **写入吞吐** | ≥ 100 条/秒（SQLite + FAISS 同步写入） | 连续调用 `insert_memory()` 1000 次，计算平均 TPS。 | `tests/test_perf_write_throughput.py` |
| **冷启动时间** | ≤ 5s（加载 Embedding 模型 + 初始化 SQLite + 加载 FAISS 索引） | 从 `SemanticMemoryEngine` 构造到首次 `process()` 可调用的耗时。 | `tests/test_perf_cold_start.py` |

### 8.4 测试基础设施

- **框架**：`pytest` + `pytest-asyncio`（异步测试）+ `pytest-cov`（覆盖率）。
- **Mock 策略**：LLM 调用统一 mock（避免真实 API 依赖），Embedding 模型使用 `BAAI/bge-small-zh-v1.5` 本地加载（CI 环境需预缓存模型）。
- **临时存储**：每个测试用例使用 `tmp_path` fixture 创建独立 SQLite + FAISS 数据目录，测试结束自动清理。
- **覆盖率命令**：`pytest --cov=llmchatflow --cov-report=term-missing --cov-fail-under=80`。
- **CI 集成**：PR 合入前必须通过全部测试且覆盖率达标。

---

## 9. 未来扩展规划 (Future)
*当前阶段暂不实现，仅做预留*：
- **Memory Decay**: 基于时间的遗忘策略 (e.g., importance < 0.2 AND older than 90 days -> delete)。
- **Memory Merging**: 合并相似记忆。
- **Memory Summarization**: 自动总结长期记忆。
