# LLM System 核心系统文档

## 1. 系统简介 (Introduction)

`llm_system` 是一个模块化、轻量级且功能完整的本地大语言模型（LLM）管理系统。它旨在为上层应用（如 Telegram Chatbot）提供统一的底层支持，涵盖了从**模型推理**、**服务接口**、**微调训练**到**效果评测**和**实验监控**的全生命周期管理。

该系统的核心设计理念是 **OpenAI 兼容性** 和 **本地化高效运行**（针对消费级显卡优化，如 4060Ti）。

---

## 2. 核心架构与组件 (Architecture & Components)

系统由以下几个核心模块组成：

### 2.1 推理引擎 (Engine) - `src/llm_system/engine`
负责加载模型并进行文本生成。
*   **BaseEngine**: 定义了推理引擎的抽象接口，确保未来可扩展支持 vLLM 等其他后端。
*   **HFRunner**: 基于 HuggingFace Transformers 的具体实现。
    *   **量化支持**: 内置 4-bit (QLoRA) 和 8-bit 量化支持，大幅降低显存占用。
    *   **流式输出**: 支持 `stream=True` 的流式文本生成。
    *   **停止控制**: 支持自定义 `stop` 停止词。

### 2.2 服务接口 (Server) - `src/llm_system/server`
基于 FastAPI 构建的 HTTP 服务层。
*   **OpenAI 兼容**: 提供 `/v1/chat/completions` 接口，完全兼容 OpenAI API 格式。这意味着你可以直接使用 `openai-python` 库或任何支持 OpenAI 协议的客户端（如 LangChain）来连接此系统。
*   **流式响应**: 完美支持 SSE (Server-Sent Events) 流式输出。

### 2.3 训练微调 (Train) - `src/llm_system/train`
提供模型微调能力，让模型更懂你的领域知识。
*   **LoRA / QLoRA**: 使用 PEFT 库实现高效微调，仅训练少量参数即可适配新任务。
*   **MLflow 集成**: 自动记录训练过程中的 Loss、Learning Rate 等指标。
*   **数据格式**: 支持标准的 JSON/JSONL 指令微调数据集。

### 2.4 评测模块 (Evaluation) - `src/llm_system/evaluation`
基于 OpenCompass 的评测包装器。
*   **自动化评测**: 支持自动加载模型并在 C-Eval, MMLU 等数据集上进行跑分。
*   **结果记录**: 评测结果自动同步至 MLflow。

### 2.5 监控模块 (Monitor) - `src/llm_system/monitor`
*   **MLflowLogger**: 统一的日志记录器，用于串联训练、推理和评测的实验数据。

---

## 3. 目录结构说明 (Directory Structure)

```text
src/llm_system/
├── data/           # 数据处理模块（待实现具体清洗逻辑）
│   ├── cleaner.py
│   └── dataset.py
├── engine/         # 推理核心
│   ├── base.py     # 抽象基类
│   └── hf_runner.py# HuggingFace 推理实现
├── evaluation/     # 评测模块
│   └── runner.py   # OpenCompass 启动器
├── monitor/        # 监控模块
│   └── mlflow_logger.py
├── server/         # API 服务层
│   ├── app.py      # FastAPI 入口
│   ├── routers.py  # 路由定义
│   └── schemas.py  # Pydantic 数据模型
└── train/          # 训练模块
    └── trainer.py  # LoRA 微调脚本
```

---

## 4. 快速开始 (Quick Start)

### 4.1 启动推理服务

如果你只想运行聊天机器人：

```bash
# 在项目根目录下运行
python -m src.llm_system.server.app
```
*   默认端口: 8000
*   API 地址: `http://localhost:8000/v1/chat/completions`

### 4.2 微调模型

如果你有自己的数据（例如 `data/train.json`），想让模型学得更好：

```bash
python src/llm_system/train/trainer.py \
    --model_path "你的模型路径" \
    --data_path "data/train.json" \
    --output_dir "checkpoints/v1"
```

### 4.3 评测模型

微调完后，看看模型变聪明了吗：

```bash
python src/llm_system/evaluation/runner.py \
    --model_path "checkpoints/v1"
```

---

## 5. 环境依赖

本系统依赖以下核心库（已包含在 `environment.yaml` 中）：
*   `torch` (CUDA 12.4+)
*   `transformers`
*   `bitsandbytes` (用于 4-bit 量化)
*   `peft` (用于 LoRA)
*   `fastapi` & `uvicorn`
*   `mlflow`
*   `opencompass` (可选，用于评测)
