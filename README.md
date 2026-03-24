# LLMChatFlow

LLMChatFlow 是一个用于管理“记忆 → 检索 → 上下文 → 推理”的轻量级 AI Infra 系统。

当前项目定位为：基于 Structured Memory + Hybrid Retrieval + Context Orchestration 的轻量级 LLM Chat Infra。

## Key Features

*   **Memory System（结构化 + 分层）**: 支持 `episodic / habit / summary`，区分 `user / session` scope，并纳入 `importance` 与 `time_decay`。
*   **Retrieval Pipeline（核心能力）**: 支持 FAISS semantic recall、type-aware scoring、bucket-based selection 与 turn-level reconstruction。
*   **Context Orchestration（关键能力）**: 贯通 memory selection → context structuring，支持 token-aware prompt 构建与 multi-source context 融合。
*   **Modular Architecture**: Session、Memory、Workflow、LLM、Adapters 解耦，便于替换与扩展。

## Architecture

(To be added)

## Quick Start

See `examples/cli_demo.py` for a basic usage example.
