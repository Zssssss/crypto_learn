FROM python:3.10-slim

WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt ./

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . /app/

# 创建必要的目录
RUN mkdir -p /app/logs /app/models/checkpoints /app/models/tensorboard

# 设置权限
RUN chmod +x /app/scripts/*.sh

# 默认命令
CMD ["python", "train_dqn.py"]