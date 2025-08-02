# 使用Python 3.11官方镜像（更稳定，支持strands-agents）
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV PYTHONUNBUFFERED=1

# 先安装基础系统依赖
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 安装Node.js 18.x
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs

# 安装其他系统依赖和Playwright所需的库
RUN apt-get update && apt-get install -y \
    fonts-liberation \
    fonts-dejavu-core \
    xvfb \
    build-essential \
    git \
    unzip \
    libxml2-dev \
    libxslt-dev \
    # Playwright系统依赖
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libfontconfig1 \
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

# 安装MCP服务器（解决strands-agents客户端初始化问题）
RUN npm install -g @executeautomation/playwright-mcp-server@1.0.6 --no-optional --no-audit --no-fund

# 复制requirements文件
COPY requirements.txt .

# 升级pip并安装Python依赖
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 安装Playwright浏览器和依赖
RUN playwright install chromium --with-deps

# 验证Playwright安装
RUN python -c "from playwright.sync_api import sync_playwright; print('Playwright installation verified')"

# 验证Node.js和strands-agents安装
RUN node --version && npx --version && \
    python -c "from strands import Agent; print('strands-agents verified')"

# 复制应用代码和配置
COPY . .

# 创建必要的目录
RUN mkdir -p logs reports test-output

# 设置权限
RUN chmod -R 755 /app

# 暴露端口
EXPOSE 8501

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# 启动命令 - 使用xvfb-run来提供虚拟显示，并指定配置文件
CMD ["xvfb-run", "-a", "streamlit", "run", "app/enhanced_streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
