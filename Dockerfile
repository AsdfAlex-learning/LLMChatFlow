# 使用官方 Python 轻量级镜像
# 推荐使用 3.12 以匹配我们的开发环境
FROM python:3.12-slim

# 设置环境变量
# PYTHONUNBUFFERED=1: 防止 Python 缓冲标准输出/错误输出，保证日志实时打印
# PYTHONDONTWRITEBYTECODE=1: 防止生成 .pyc 文件
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安装系统级依赖 (编译 mmcv 或其他扩展可能需要)
# git: 用于安装 git 依赖
# libgl1: OpenCV (mmcv 依赖) 需要
# libglib2.0-0: OpenCV 需要
RUN apt-get update && apt-get install -y \
    git \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .

# 1. 安装核心依赖
RUN pip install --no-cache-dir -r requirements.txt

# 2. 安装 MMCV (使用 mim)
# 在 Docker 中构建时，我们需要显式安装它
RUN pip install --no-cache-dir openmim && \
    mim install "mmcv>=2.0.0"

# 复制项目所有文件
COPY . .

# 暴露端口 (如果有 Web 服务)
EXPOSE 8080

# 启动命令
CMD ["python", "run.py"]
