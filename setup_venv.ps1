# ==========================================
# Telegram Chatbot VENV 自动化配置脚本 (Windows PowerShell)
# ==========================================

$VenvDir = "venv"

Write-Host "🚀 开始 VENV 环境配置..." -ForegroundColor Cyan

# 1. 检测 Python
# 尝试寻找 python 3.12/3.11，或者直接用 python
function Get-PythonCommand {
    if (Get-Command python3.12 -ErrorAction SilentlyContinue) { return "python3.12" }
    if (Get-Command python -ErrorAction SilentlyContinue) { 
        # 检查版本
        $ver = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        if ([version]$ver -ge [version]"3.9") { return "python" }
    }
    return $null
}

$PythonCmd = Get-PythonCommand

if (-not $PythonCmd) {
    Write-Host "❌ 错误: 未找到合适的 Python (需要 3.9+)。请安装 Python 并添加到 PATH。" -ForegroundColor Red
    exit 1
}

Write-Host "ℹ️  使用 Python 解释器: $PythonCmd" -ForegroundColor Gray

# 2. 创建虚拟环境
if (Test-Path $VenvDir) {
    Write-Host "ℹ️  虚拟环境 '$VenvDir' 已存在，跳过创建。" -ForegroundColor Yellow
} else {
    Write-Host "📦 创建虚拟环境 '$VenvDir'..." -ForegroundColor Cyan
    & $PythonCmd -m venv $VenvDir
}

# 3. 定位 Venv 中的 pip 和 python
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "❌ 错误: 虚拟环境创建似乎失败了，找不到 $VenvPython" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 环境已就绪: $VenvPython" -ForegroundColor Green

# 4. 升级 pip
Write-Host "⬆️  升级 pip..." -ForegroundColor Gray
& $VenvPython -m pip install --upgrade pip

# 5. 修复潜在冲突 (telebot)
Write-Host "🧹 清理潜在的包冲突..." -ForegroundColor Cyan
& $VenvPip uninstall -y telebot PyTelegramBotAPI *>$null

# 6. 安装核心依赖
if (Test-Path "requirements.txt") {
    Write-Host "📥 安装核心依赖 (requirements.txt)..." -ForegroundColor Cyan
    
    # Windows 上 pip install torch 通常会自动选择带 CUDA 的版本 (如果可用) 或 CPU 版本
    # 所以直接安装即可，不需要像 Linux 那样手动指定 index-url
    & $VenvPip install -r requirements.txt
} else {
    Write-Host "⚠️  未找到 requirements.txt，跳过依赖安装。" -ForegroundColor Yellow
}

# 7. 特殊处理 MMCV (OpenMMLab)
Write-Host "🔧 处理 MMCV 依赖..." -ForegroundColor Cyan
& $VenvPip install -U openmim

Write-Host "📥 使用 mim 安装 mmcv>=2.0.0..." -ForegroundColor Cyan
# 在 Windows venv 中，mim.exe 位于 Scripts 目录下
$MimCmd = Join-Path $VenvDir "Scripts\mim.exe"
if (-not (Test-Path $MimCmd)) {
    # Fallback
    $MimCmd = "mim" 
}

# 注意：在 PowerShell 中直接调用可能需要用 python -m mim，或者直接调用 exe
if (Test-Path $MimCmd) {
    & $MimCmd install "mmcv>=2.0.0"
} else {
    # 如果找不到 mim.exe，尝试通过模块调用
    & $VenvPython -m mim install "mmcv>=2.0.0"
}

Write-Host "==========================================" -ForegroundColor Green
Write-Host "🎉 VENV 环境配置完成！" -ForegroundColor Green
Write-Host "请在 PowerShell 中运行以下命令激活环境：" -ForegroundColor Yellow
Write-Host "    .\$VenvDir\Scripts\Activate.ps1" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Green
