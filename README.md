# TelegramChatbot

A sophisticated Telegram Chatbot powered by **Nonebot** and LLMs (OpenAI-compatible APIs like DeepSeek). Designed with a **Kernel-Satellite Architecture**, it features advanced memory management, proactive messaging, and human-like interaction rhythm.

> ⚠️ **Note**: For detailed documentation (Chinese), please refer to:
> - [Installation Guide](docs/zh-CN/INSTALL.md)
> - [Architecture & Design](docs/zh-CN/ARCHITECTURE.md)
> - [Development Guide](docs/zh-CN/DEVELOPMENT.md)

## ✨ Key Features

- **Kernel-Satellite Architecture**: Separation of core logic (`src/core`) from protocol adapters (`src/bot`), ensuring stability and scalability.
- **Empathy Agent Core**:
  - **EmpathyPlanner**: Rule-based decision engine for emotional state and reply strategies.
  - **ExpressionOrchestrator**: Multi-modal response generation (Text, Action, Mood).
  - **PersonaState**: Inner state tracking (Relationship Stage, Emotion).
- **Human-like Interaction**:
  - **Rhythm Control**: `InteractionManager` buffers messages and simulates natural typing delays.
  - **Fragmented Speech**: Breaks long responses into natural segments.
- **Advanced Memory System**:
  - **Short-term**: Context window management.
  - **Long-term**: Structured memory ingestion and retrieval (Active Development).
- **Proactive Messaging**: `ProactiveService` with Policy/Agent pattern to initiate conversations based on user activity and memory.
- **Robustness**:
  - **Session Control**: Thread-safe session management with strict permission checks.
  - **Unified Logging**: Comprehensive, rotating logs for debugging.
  - **Dockerized**: Ready-to-deploy with Docker support.

## 🚀 Quick Start

### 1. Auto Setup (Recommended)
We provide automated scripts to set up the environment (supports Conda and venv).

#### macOS / Linux
```bash
# For Conda users
./setup_env.sh

# For venv (Standard Python) users
./setup_venv.sh
```

#### Windows (PowerShell)
```powershell
# For Conda users
.\setup_env.ps1

# For venv (Standard Python) users
.\setup_venv.ps1
```

### 2. Manual Setup
If you prefer manual installation:

```bash
# Install core dependencies
pip install -r requirements.txt

# Install mmcv (Required for evaluation, using mim is recommended)
pip install openmim
mim install "mmcv>=2.0.0"
```

### 3. Run
```bash
# Ensure you have configured your keys in config/
python run.py
```

### Using Docker
```bash
# Build the image
docker build -t telegram-chatbot .

# Run (Mount your configuration file)
docker run -d --name my-bot -p 8080:8080 -v $(pwd)/config:/app/config telegram-chatbot
```

## 📂 Project Structure

```
src/
├── agent/          # Agent Core: Planner, Orchestrator, State, Skills
├── core/           # Kernel: Business logic, State, Config, Logging
├── bot/            # Satellite: Telegram Adapter, Handlers, Scheduling
├── llm_system/     # LLM Training & Evaluation Pipeline
├── api/            # External Integrations (e.g., Weather)
├── storage/        # Data Persistence
└── config/         # YAML Configurations
```

## 📝 Declaration

Rather than a fully-featured, polished chatbot, this project is more like the very first side project of an average (or even arguably unskilled) computer science student starting from scratch. It contains a lot of personal, subjective elements, so the code and documentation may not be concise or accurate enough.
