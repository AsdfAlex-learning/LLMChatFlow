#!/bin/bash

# ==========================================
# Telegram Chatbot 环境自动配置脚本 (macOS/Linux)
# ==========================================

ENV_NAME="telegram_chatbot"
PYTHON_VERSION="3.12"

echo "🚀 开始环境配置..."

# 1. 检查 Conda 是否安装
if ! command -v conda &> /dev/null; then
    echo "❌ 错误: 未检测到 Conda。请先安装 Anaconda 或 Miniconda。"
    exit 1
fi

# 2. 初始化 Conda (确保 shell 能使用 conda activate)
# 尝试找到 conda.sh
CONDA_BASE=$(conda info --base)
source "$CONDA_BASE/etc/profile.d/conda.sh"

# 3. 创建/更新 Conda 环境
if conda info --envs | grep -q "^$ENV_NAME "; then
    echo "ℹ️  环境 '$ENV_NAME' 已存在，正在激活..."
else
    echo "📦 创建新环境 '$ENV_NAME' (Python $PYTHON_VERSION)..."
    conda create -n $ENV_NAME python=$PYTHON_VERSION -y
fi

# 激活环境
conda activate $ENV_NAME
if [ $? -ne 0 ]; then
    echo "❌ 激活环境失败。"
    exit 1
fi

echo "✅ 环境已激活: $(which python)"

# 4. 修复潜在的 telebot 冲突 (必杀技)
echo "🧹 清理潜在的包冲突..."
pip uninstall -y telebot PyTelegramBotAPI > /dev/null 2>&1 || true

# 5. 安装核心依赖 (从 requirements.txt)
if [ -f "requirements.txt" ]; then
    echo "📥 安装核心依赖 (pip)..."
    # 临时禁用 mmcv 以防卡死，虽然 requirements.txt 里已经注释了，这里双重保险
    pip install -r requirements.txt
else
    echo "⚠️  未找到 requirements.txt，跳过依赖安装。"
fi

# 6. 特殊处理 MMCV (OpenMMLab)
echo "🔧 处理 MMCV 依赖..."
# 安装 openmim
pip install -U openmim

# 使用 mim 安装 mmcv (会自动选择正确的预编译包)
echo "📥 使用 mim 安装 mmcv>=2.0.0..."
mim install "mmcv>=2.0.0"

echo "=========================================="
echo "🎉 环境配置完成！"
echo "请在终端运行以下命令激活环境："
echo "    conda activate $ENV_NAME"
echo "=========================================="
