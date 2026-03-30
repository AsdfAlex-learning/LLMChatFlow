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
1.  **Application Layer**: `chat_engine` (对话编排)
2.  **AI Layer**: `embedding` / `llm` (模型服务)
3.  **Retrieval Layer**: `FAISS` (向量索引)
4.  **Storage Layer**: `SQLite` (元数据存储)

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
│   │   ├── postprocess/                # 输出后处理
│   │   ├── prompt/                     # Prompt 组装与 token 预算
│   │   ├── session/                    # 会话状态管理
│   │   └── workflow/
│   │       └── engine.py               # 对话工作流编排
│   └── utils/
│       ├── embedding.py                # 向量工具
│       ├── sqlite_helper.py            # SQLite 辅助封装
│       └── token_counter.py            # Token 计数
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
- **文件**: `core/chat_engine.py`
- **职责**: 整个对话流程的 Orchestrator。
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
- **文件**: `embedding/embedder.py`
- **模型**: `BAAI/bge-small-zh`
- **职责**: 文本 -> 向量 (Float32, Normalized)。
- **设计原则**: 独立模块，未来可替换模型。

### 4.3 Vector Store (FAISS)
- **文件**: `retrieval/vector_store.py`
- **职责**: 向量索引管理 (Add, Search, Load, Save)。
- **实现**: 使用 `faiss.IndexFlatIP` (Inner Product) 或适合的索引类型。

### 4.4 SQLite Metadata Storage
- **文件**: `storage/sqlite_store.py`
- **职责**: 存储记忆的元数据、会话管理以及参与者关系。

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
在 `memory/` 下新增策略层：
```text
memory/
  manager.py
  retriever.py
  scorer.py
  policy/
    base.py
    default.py
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
```text
core/memory/
  retrieval.py
  view_builder.py
```

交付要求：
- `retrieve()` 专注高质量结构化召回
- `build_view()` 负责可控格式化与 token 约束

---

## 8. 未来扩展规划 (Future)
*当前阶段暂不实现，仅做预留*：
- **Memory Decay**: 基于时间的遗忘策略 (e.g., importance < 0.2 AND older than 90 days -> delete)。
- **Memory Merging**: 合并相似记忆。
- **Memory Summarization**: 自动总结长期记忆。
