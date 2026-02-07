# 使用 Python 3.11 官方镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \

# 配置 apt 使用清华镜像源（加速系统包安装）
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        curl \
        && rm -rf /var/lib/apt/lists/*

# 配置 pip 使用清华镜像源并安装 uv
RUN pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/simple && \
    pip config set global.trusted-host mirrors.tuna.tsinghua.edu.cn && \
    pip install --no-cache-dir uv

# 复制项目文件
COPY . .

# 安装 Python 依赖
RUN uv sync --frozen --no-dev

# 暴露端口 (FastAPI/uvicorn 默认端口)
EXPOSE 8000

# 运行应用
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
