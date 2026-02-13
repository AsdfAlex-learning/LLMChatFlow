# 安装与运行说明

## 环境要求

- **操作系统**: macOS, Linux, 或 Windows
- **Python**: 3.9+ (推荐 3.12)
- **可选**: Anaconda / Miniconda (如果不使用 venv)

## 快速开始 (推荐)

我们提供了全自动的安装脚本，可以自动检测系统环境、安装依赖并修复常见冲突（如 telebot 冲突、mmcv 安装困难等）。

### 1. 自动配置环境

请根据你的操作系统和偏好选择对应的脚本：

#### macOS / Linux

**如果你使用 Conda:**
```bash
chmod +x setup_env.sh
./setup_env.sh
```

**如果你使用原生 Python venv:**
```bash
chmod +x setup_venv.sh
./setup_venv.sh
```

#### Windows (PowerShell)

**如果你使用 Conda:**
```powershell
.\setup_env.ps1
```

**如果你使用原生 Python venv:**
```powershell
.\setup_venv.ps1
```

### 2. 激活环境

脚本运行结束后会提示激活命令，通常如下：

- **Conda**: `conda activate telegram_chatbot`
- **macOS/Linux venv**: `source venv/bin/activate`
- **Windows venv**: `.\venv\Scripts\Activate.ps1`

### 3. 配置密钥

请参考 `config/example_system.yaml` 复制一份为 `config/system.yaml`（或其他实际使用的配置文件名），并填入你的 Telegram Token 和 LLM API Key。

### 4. 运行项目

```bash
python run.py
```

---

## 手动安装 (如果不使用脚本)

如果你希望手动控制安装过程，请遵循以下步骤：

1.  **安装核心依赖**:
    ```bash
    pip install -r requirements.txt
    ```
    *注意：requirements.txt 中已注释掉 mmcv，以防安装失败。*

2.  **安装 MMCV (OpenCompass 评测必需)**:
    为了避免编译错误，建议使用 OpenMMLab 官方的 `mim` 工具安装：
    ```bash
    pip install openmim
    mim install "mmcv>=2.0.0"
    ```

3.  **启动**:
    ```bash
    python run.py
    ```

## Docker 部署

```bash
# 1. 构建镜像
docker build -t telegram-chatbot .

# 2. 运行容器 (请确保挂载了配置目录)
# 假设你的配置文件在当前目录的 config/ 文件夹下
docker run -d \
  --name my-bot \
  -v $(pwd)/config:/app/config \
  telegram-chatbot
```
