# ==========================================
# Telegram Chatbot 环境自动配置脚本 (Windows PowerShell)
# ==========================================

$EnvName = "telegram_chatbot"
$PythonVersion = "3.12"

Write-Host "🚀 开始环境配置..." -ForegroundColor Cyan

# 1. 检查 Conda 是否安装
if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    Write-Host "❌ 错误: 未检测到 Conda。请先安装 Anaconda 或 Miniconda 并添加到 PATH。" -ForegroundColor Red
    exit 1
}

# 2. 创建/检查 Conda 环境
$Envs = conda info --envs
if ($Envs -match "$EnvName") {
    Write-Host "ℹ️  环境 '$EnvName' 已存在。" -ForegroundColor Yellow
} else {
    Write-Host "📦 创建新环境 '$EnvName' (Python $PythonVersion)..." -ForegroundColor Cyan
    conda create -n $EnvName python=$PythonVersion -y
}

# 3. 激活环境 (PowerShell 中比较特殊，通常建议用户手动激活，但我们可以尝试直接调用 pip)
# 获取该环境的 pip 路径
$CondaBase = conda info --base
$EnvPath = Join-Path $CondaBase "envs\$EnvName"
if (-not (Test-Path $EnvPath)) {
    # 如果环境不在默认路径，尝试解析 conda info
    # 这里简单处理，假设用户使用标准路径。如果失败，提示用户手动激活。
    Write-Host "⚠️  无法自动定位环境路径，将尝试在当前 Shell 激活..." -ForegroundColor Yellow
    conda activate $EnvName
}

$PipCmd = Join-Path $EnvPath "Scripts\pip.exe"
$PythonCmd = Join-Path $EnvPath "python.exe"

if (-not (Test-Path $PipCmd)) {
    # Fallback: 尝试直接运行 pip，假设用户已经激活
    $PipCmd = "pip"
    $PythonCmd = "python"
}

Write-Host "正在使用 pip: $PipCmd" -ForegroundColor Gray

# 4. 修复潜在的 telebot 冲突
Write-Host "🧹 清理潜在的包冲突..." -ForegroundColor Cyan
& $PipCmd uninstall -y telebot PyTelegramBotAPI *>$null

# 5. 安装核心依赖
if (Test-Path "requirements.txt") {
    Write-Host "📥 安装核心依赖 (pip)..." -ForegroundColor Cyan
    & $PipCmd install -r requirements.txt
} else {
    Write-Host "⚠️  未找到 requirements.txt，跳过依赖安装。" -ForegroundColor Yellow
}

# 6. 特殊处理 MMCV
Write-Host "🔧 处理 MMCV 依赖..." -ForegroundColor Cyan
& $PipCmd install -U openmim

Write-Host "📥 使用 mim 安装 mmcv>=2.0.0..." -ForegroundColor Cyan
# mim 是一个可执行脚本，在 Windows Scripts 目录下
$MimCmd = Join-Path $EnvPath "Scripts\mim.exe"
if (-not (Test-Path $MimCmd)) {
    $MimCmd = "mim"
}

& $MimCmd install "mmcv>=2.0.0"

Write-Host "==========================================" -ForegroundColor Green
Write-Host "🎉 环境配置完成！" -ForegroundColor Green
Write-Host "请运行以下命令激活环境：" -ForegroundColor Yellow
Write-Host "    conda activate $EnvName" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Green
