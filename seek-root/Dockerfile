FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（用于WeasyPrint PDF生成）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8050

# 环境变量
ENV PORT=8050
ENV HOST=0.0.0.0
ENV DATABASE_URL=sqlite:///./data/seek_root.db

# 启动命令
CMD ["seek-root", "serve", "--host", "0.0.0.0", "--port", "8050"]
