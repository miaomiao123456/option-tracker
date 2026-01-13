#!/bin/bash

# 阿里云ECS一键部署脚本
# 适用于Ubuntu 20.04/22.04 或 CentOS 7/8

set -e

echo "=========================================="
echo "OptionAlpha 期权交易策略系统"
echo "阿里云部署脚本"
echo "=========================================="

# 检测操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
else
    echo "无法检测操作系统"
    exit 1
fi

echo "检测到操作系统: $OS"

# 1. 安装Docker
echo ""
echo "[步骤 1/5] 安装 Docker..."
if ! command -v docker &> /dev/null; then
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        # Ubuntu/Debian
        sudo apt-get update
        sudo apt-get install -y ca-certificates curl gnupg
        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg

        echo \
          "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
          sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
        # CentOS/RHEL
        sudo yum install -y yum-utils
        sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        sudo systemctl start docker
        sudo systemctl enable docker
    fi
    echo "✓ Docker 安装完成"
else
    echo "✓ Docker 已安装"
fi

# 2. 安装Docker Compose (如果使用旧版)
echo ""
echo "[步骤 2/5] 检查 Docker Compose..."
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "安装 Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✓ Docker Compose 安装完成"
else
    echo "✓ Docker Compose 已安装"
fi

# 3. 创建项目目录
echo ""
echo "[步骤 3/5] 创建项目目录..."
PROJECT_DIR="/opt/option-tracker"
sudo mkdir -p $PROJECT_DIR
sudo chown -R $USER:$USER $PROJECT_DIR
cd $PROJECT_DIR
echo "✓ 项目目录创建完成: $PROJECT_DIR"

# 4. 配置环境变量
echo ""
echo "[步骤 4/5] 配置环境变量..."
if [ ! -f .env.production ]; then
    cat > .env.production << 'EOF'
# 数据库配置
DATABASE_URL=sqlite:///./data/option_tracker.db

# 优矿API Token (必填)
UQER_TOKEN=your_uqer_token_here

# AI配置 (选填)
GEMINI_API_KEY=
GEMINI_BASE_URL=https://www.apillm.online/v1

# 应用配置
DEBUG=False
LOG_LEVEL=INFO
PORT=8001

# CORS配置
ALLOWED_ORIGINS=*

# 性能配置
WORKERS=2
MAX_CONNECTIONS=100
EOF
    echo "✓ 环境变量文件已创建: .env.production"
    echo "  请编辑 .env.production 填入你的配置"
else
    echo "✓ 环境变量文件已存在"
fi

# 5. 提示上传代码
echo ""
echo "[步骤 5/5] 准备部署..."
echo ""
echo "=========================================="
echo "请按以下步骤完成部署:"
echo "=========================================="
echo ""
echo "1. 将项目代码上传到服务器:"
echo "   scp -r /Users/pm/Documents/期权交易策略/option_tracker/* root@your-server-ip:$PROJECT_DIR/"
echo ""
echo "2. 或者使用Git克隆:"
echo "   cd $PROJECT_DIR"
echo "   git clone <your-repo-url> ."
echo ""
echo "3. 编辑环境变量:"
echo "   nano $PROJECT_DIR/.env.production"
echo ""
echo "4. 启动服务:"
echo "   cd $PROJECT_DIR"
echo "   docker compose -f docker-compose.prod.yml up -d --build"
echo ""
echo "5. 查看日志:"
echo "   docker compose -f docker-compose.prod.yml logs -f"
echo ""
echo "6. 配置防火墙开放8001端口:"
echo "   sudo ufw allow 8001/tcp  # Ubuntu"
echo "   sudo firewall-cmd --permanent --add-port=8001/tcp  # CentOS"
echo "   sudo firewall-cmd --reload  # CentOS"
echo ""
echo "7. 访问应用:"
echo "   http://your-server-ip:8001/frontend.html"
echo ""
echo "=========================================="
echo "安装完成! 🎉"
echo "=========================================="
