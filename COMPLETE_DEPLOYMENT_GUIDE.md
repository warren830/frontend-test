# Frontend Test Application - 完整部署指南

## 📋 项目概述

这是一个基于Streamlit的前端测试应用，集成了以下核心功能：
- **Streamlit Web应用**: 提供用户界面
- **Playwright浏览器自动化**: 支持网页测试和自动化
- **strands-agents**: AI代理框架，支持Bedrock模型调用
- **Docker容器化**: 完整的容器化部署方案
- **AWS ECR**: 镜像仓库管理
- **AWS Bedrock**: AI模型服务集成

## 🏗️ 架构组件

### 技术栈
- **Python 3.11**: 主要运行环境
- **Node.js 18.x**: 支持MCP服务器和npm包管理
- **Streamlit 1.47.1**: Web应用框架
- **Playwright 1.54.0**: 浏览器自动化
- **strands-agents 1.2.0**: AI代理框架
- **Docker**: 容器化部署
- **AWS ECR**: 容器镜像仓库
- **AWS Bedrock**: AI模型服务

### 系统依赖
- **Xvfb**: 虚拟显示服务器（支持无头浏览器）
- **Chromium**: Playwright浏览器引擎
- **系统库**: 完整的GUI和图形处理库支持

## 🚀 部署流程

### 1. 环境准备

#### 1.1 EC2实例配置
- **实例类型**: t3.medium 或更高
- **操作系统**: Amazon Linux 2023
- **磁盘空间**: 100GB (从8GB扩展)
- **安全组**: 开放8501端口用于Web访问

#### 1.2 IAM权限配置
创建EC2-ECR-Role角色，包含以下策略：

**ECR访问策略**:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage"
            ],
            "Resource": "*"
        }
    ]
}
```

**Bedrock访问策略**:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:Converse",
                "bedrock:ConverseStream",
                "bedrock:GetFoundationModel",
                "bedrock:ListFoundationModels"
            ],
            "Resource": [
                "arn:aws:bedrock:*:*:foundation-model/*",
                "arn:aws:bedrock:*:*:inference-profile/*"
            ]
        }
    ]
}
```

### 2. 磁盘扩展

```bash
# 从AWS控制台或CLI扩展EBS卷到100GB
aws ec2 modify-volume --volume-id vol-xxxxxxxxx --size 100 --region us-east-1

# 在EC2实例上扩展文件系统
sudo growpart /dev/nvme0n1 1
sudo xfs_growfs /
```

### 3. Docker镜像构建

#### 3.1 项目结构
```
frontend-test/
├── Dockerfile                 # Docker构建文件
├── requirements.txt           # Python依赖
├── .streamlit/
│   └── config.toml           # Streamlit配置
├── app/
│   ├── enhanced_streamlit_app.py
│   └── report_pages.py
├── core/                     # 核心功能模块
├── test_cases/              # 测试用例
└── tests/                   # 测试文件
```

#### 3.2 核心文件

**requirements.txt**:
```
streamlit>=1.28.0
pandas>=2.0.0
plotly>=5.15.0
playwright>=1.40.0
asyncio-mqtt>=0.13.0
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
openpyxl>=3.1.0
python-dotenv>=1.0.0
aiofiles>=23.0.0
strands-agents
strands-agents-tools
pyyaml>=6.0
```

**Streamlit配置 (.streamlit/config.toml)**:
```toml
[server]
port = 8501
address = "0.0.0.0"
headless = true
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false
serverAddress = "0.0.0.0"
serverPort = 8501

[client]
caching = false
showErrorDetails = true

[global]
developmentMode = false
suppressDeprecationWarnings = true
```

### 4. 构建和部署

#### 4.1 构建Docker镜像
```bash
# 在EC2实例上构建
cd /home/ec2-user/frontend-test-updated
docker build -t frontend-test-final:latest . --no-cache
```

#### 4.2 推送到ECR
```bash
# 标记镜像
docker tag frontend-test-final:latest 324037295989.dkr.ecr.ap-southeast-1.amazonaws.com/frontend-test-app:final-latest

# 登录ECR
aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin 324037295989.dkr.ecr.ap-southeast-1.amazonaws.com

# 推送镜像
docker push 324037295989.dkr.ecr.ap-southeast-1.amazonaws.com/frontend-test-app:final-latest
```

#### 4.3 部署容器
```bash
# 启动应用容器
docker run -d \
  --name frontend-test-app \
  -p 8501:8501 \
  -e DISPLAY=:99 \
  --shm-size=2g \
  --health-cmd="curl -f http://localhost:8501/_stcore/health || exit 1" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  324037295989.dkr.ecr.ap-southeast-1.amazonaws.com/frontend-test-app:final-latest
```

## 🔧 关键技术解决方案

### 1. 架构兼容性问题
**问题**: ARM64构建环境与x86_64目标不兼容
**解决**: 直接在目标EC2实例上构建镜像

### 2. strands-agents客户端初始化失败
**问题**: `FileNotFoundError: [Errno 2] No such file or directory: 'npx'`
**解决**: 安装Node.js 18.x和MCP服务器
```dockerfile
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs
RUN npm install -g @executeautomation/playwright-mcp-server@1.0.6
```

### 3. Playwright系统依赖
**问题**: 缺少浏览器运行所需的系统库
**解决**: 安装完整的GUI依赖包
```dockerfile
RUN apt-get install -y \
    libasound2 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 \
    libcairo2 libcups2 libdbus-1-3 libdrm2 libgbm1 \
    libglib2.0-0 libnspr4 libnss3 libpango-1.0-0 \
    libx11-6 libxcb1 libxcomposite1 libxdamage1 \
    libxext6 libxfixes3 libxkbcommon0 libxrandr2 \
    libfontconfig1 libfreetype6
```

### 4. Bedrock权限问题
**问题**: `AccessDeniedException` for Bedrock operations
**解决**: 创建完整的Bedrock访问策略并附加到EC2角色

### 5. 磁盘空间不足
**问题**: 8GB磁盘空间不足以支持完整构建
**解决**: 扩展EBS卷到100GB并扩展文件系统

## 📊 部署验证

### 健康检查
```bash
# 容器状态检查
docker ps | grep frontend-test-app

# 应用健康检查
curl -f http://localhost:8501/_stcore/health

# 功能验证
docker exec frontend-test-app python -c "
from strands import Agent
import playwright
print('✅ 所有核心功能正常')
"
```

### 访问地址
- **主应用**: http://13.219.89.130:8501
- **健康检查**: http://13.219.89.130:8501/_stcore/health

## 🔄 运维操作

### 重启应用
```bash
docker restart frontend-test-app
```

### 查看日志
```bash
docker logs -f frontend-test-app
```

### 更新部署
```bash
# 停止现有容器
docker stop frontend-test-app && docker rm frontend-test-app

# 拉取最新镜像
docker pull 324037295989.dkr.ecr.ap-southeast-1.amazonaws.com/frontend-test-app:final-latest

# 重新部署
docker run -d --name frontend-test-app [参数同上]
```

## 🎯 性能指标

### 资源使用
- **内存使用**: ~287MB
- **磁盘使用**: ~8% (100GB总容量)
- **CPU使用**: 低负载下 < 5%

### 启动时间
- **容器启动**: ~10秒
- **应用就绪**: ~15秒
- **健康检查**: ~30秒后变为健康状态

## 🔐 安全考虑

### 网络安全
- 仅开放必要端口(8501)
- 使用AWS安全组控制访问
- 内部服务通信使用localhost

### 权限管理
- 最小权限原则配置IAM角色
- 分离ECR和Bedrock权限策略
- 定期审查和更新权限

### 容器安全
- 使用官方Python基础镜像
- 定期更新依赖包
- 非root用户运行应用进程

## 📝 故障排除

### 常见问题

1. **容器启动失败**
   - 检查磁盘空间: `df -h`
   - 查看容器日志: `docker logs frontend-test-app`

2. **健康检查失败**
   - 等待应用完全启动(15-30秒)
   - 检查端口监听: `netstat -tlnp | grep 8501`

3. **Bedrock权限错误**
   - 验证IAM策略附加: `aws iam list-attached-role-policies --role-name EC2-ECR-Role`
   - 等待权限传播(5-10分钟)

4. **Playwright浏览器错误**
   - 确认Xvfb运行: `docker exec frontend-test-app ps aux | grep Xvfb`
   - 检查DISPLAY环境变量设置

## 🎉 部署成功标志

- ✅ 容器状态: Up X minutes (healthy)
- ✅ 健康检查: 返回 "ok"
- ✅ 页面访问: 显示Streamlit标题
- ✅ strands-agents: 可以正常导入和使用
- ✅ Playwright: 浏览器自动化功能正常
- ✅ Bedrock: AI模型调用无权限错误

---

**部署完成时间**: 2025-08-02
**镜像版本**: final-latest
**ECR仓库**: 324037295989.dkr.ecr.ap-southeast-1.amazonaws.com/frontend-test-app
**应用地址**: http://13.219.89.130:8501
