# Memory Intelligence Layer

## OVERVIEW
记忆智能层——LLMChatFlow 的核心差异化能力。封装 FAISS recall → type-aware scoring → bucket-based selection → turn-level reconstruction 的完整检索决策链。

## WHERE TO LOOK

| 模块 | 文件 | 职责 |
|------|------|------|
| 策略接口 | `policy/base.py` | `MemoryPolicy` ABC: `score()` + `select()` |
| 默认策略 | `policy/default.py` | 类型感知评分 + 桶选择 (60/30/10) |
| 统一入口 | `manager.py` | `MemoryManager`: retrieve/store/build_view |
| 检索编排 | `retriever.py` | Embed→FAISS→Score→Select→Group，支持 Filter First / Recall First |
| 表现层 | `view_builder.py` | 检索结果 → text/prompt/structured 三种格式，token 裁剪 |
| 评分函数 | `ranking.py` | `temporal_score`, `recency_scores`, `compute_final_scores_by_type` |
| 语义回退 | `semantic.py` | FAISS 不可用时的 cosine similarity fallback |
| LLM 判定 | `judge.py` | `LLMJudge`: 记忆类型分类 + 重要性评分 |
| 存储接口 | `storage.py` | `MemoryStore` ABC: insert_memory/insert_message/fetch/search |

## CONVENTIONS
- 策略可插拔：`DefaultMemoryPolicy` 覆盖 80% 场景，通过 `CustomPolicy(MemoryPolicy)` 扩展
- Headless API：`MemoryManager.retrieve()` 不依赖 LLM，仅返回结构化记忆数据
- View Builder 不持久化：返回内容为 derived data，不落库
- Bucket 配额：episodic 60% / habit 30% / summary 剩余（不小于 1 条 episodic）

## ANTI-PATTERNS
- ❌ 在 `select()` 中硬编码评分权重 — 通过 config 或 kwargs 传入
- ❌ 直接调用 `ranking.py` 函数绕过 MemoryPolicy — 用 `policy.select()`
- ❌ 在 retriever 中处理 view 格式化 — 用 `view_builder.build_view()`
