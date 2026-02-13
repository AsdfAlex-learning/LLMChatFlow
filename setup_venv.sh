#!/bin/bash

# ==========================================
# Telegram Chatbot VENV 自动化配置脚本 (macOS/Linux)
# ==========================================

VENV_DIR="venv"

echo "🚀 开始 VENV 环境配置..."

# 1. 检测 Python 版本
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
else
    PYTHON_CMD="python3"
fi

echo "ℹ️  使用 Python 解释器: $PYTHON_CMD"
# 简单的版本检查
PY_VER=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [[ "$PY_VER" < "3.9" ]]; then
    echo "❌ 错误: Python 版本过低 ($PY_VER)。需要 Python 3.9+。"
    exit 1
fi

# 2. 创建虚拟环境
if [ -d "$VENV_DIR" ]; then
    echo "ℹ️  虚拟环境 '$VENV_DIR' 已存在，跳过创建。"
else
    echo "📦 创建虚拟环境 '$VENV_DIR'..."
    $PYTHON_CMD -m venv $VENV_DIR
fi

# 3. 激活环境
source $VENV_DIR/bin/activate
echo "✅ 环境已激活: $(which python)"

# 4. 升级 pip
echo "⬆️  升级 pip..."
pip install --upgrade pip

# 5. 修复潜在冲突 (telebot)
echo "🧹 清理潜在的包冲突..."
pip uninstall -y telebot PyTelegramBotAPI > /dev/null 2>&1 || true

# 6. 安装核心依赖
if [ -f "requirements.txt" ]; then
    echo "📥 安装核心依赖 (requirements.txt)..."
    
    # 智能检测是否需要安装 CUDA 版 PyTorch (针对 Linux)
    # macOS 和 Windows 通常由 pip 自动处理，但在 Linux 上 pip 默认可能只装 CPU 版
    if [[ "$OSTYPE" == "linux-gnu"* ]] && command -v nvidia-smi &> /dev/null; then
        echo "🐧 检测到 Linux + NVIDIA GPU，优先安装 CUDA 版 PyTorch..."
        # 预先安装 CUDA 版 PyTorch，避免 requirements.txt 安装 CPU 版
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    fi

    # 安装其余依赖
    pip install -r requirements.txt
else
    echo "⚠️  未找到 requirements.txt，跳过依赖安装。"
fi

# 7. 特殊处理 MMCV (OpenMMLab)
echo "🔧 处理 MMCV 依赖..."
pip install -U openmim
echo "📥 使用 mim 安装 mmcv>=2.0.0..."
mim install "mmcv>=2.0.0"

echo "=========================================="
echo "🎉 VENV 环境配置完成！"
echo "请在终端运行以下命令激活环境："
echo "    source $VENV_DIR/bin/activate"
echo "=========================================="
