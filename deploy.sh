#!/bin/bash
# OptionAlpha 一键部署脚本（Oracle Cloud / Ubuntu）

set -e

echo "========================================="
echo "  OptionAlpha 期权交易跟踪器部署脚本"
echo "========================================="
echo ""

# 检测系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "无法检测操作系统"
    exit 1
fi

echo "检测到系统: $OS"
echo ""

# 更新系统
echo "[1/8] 更新系统包..."
sudo apt update && sudo apt upgrade -y

# 安装Python和pip
echo "[2/8] 安装Python3和pip..."
sudo apt install -y python3 python3-pip python3-venv git

# 克隆项目（如果还没有）
if [ ! -d "option_tracker" ]; then
    echo "[3/8] 克隆项目..."
    read -p "请输入GitHub仓库地址（留空跳过）: " repo_url
    if [ -n "$repo_url" ]; then
        git clone "$repo_url" option_tracker
    else
        echo "请手动上传项目文件到 ~/option_tracker"
        exit 0
    fi
fi

cd option_tracker

# 创建虚拟环境
echo "[4/8] 创建Python虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 安装依赖
echo "[5/8] 安装Python依赖..."
pip install -r requirements.txt

# 安装Playwright
echo "[6/8] 安装Playwright浏览器..."
playwright install-deps
playwright install chromium

# 配置环境变量
echo "[7/8] 配置环境变量..."
if [ ! -f .env ]; then
    read -p "请输入交易可查账号: " jyk_user
    read -sp "请输入交易可查密码: " jyk_pass
    echo ""
    read -p "请输入Gemini API Key: " gemini_key

    cat > .env << EOF
DATABASE_URL=sqlite:///./option_tracker.db
REDIS_URL=redis://localhost:6379/0
JYK_USER=$jyk_user
JYK_PASS=$jyk_pass
GEMINI_API_KEY=$gemini_key
GEMINI_BASE_URL=https://www.apillm.online/v1
DEBUG=True
LOG_LEVEL=INFO
EOF
    echo ".env 文件已创建"
else
    echo ".env 文件已存在，跳过"
fi

# 创建systemd服务
echo "[8/8] 创建systemd服务..."
WORK_DIR=$(pwd)
PYTHON_PATH="$WORK_DIR/venv/bin/python"

sudo tee /etc/systemd/system/option-tracker.service > /dev/null << EOF
[Unit]
Description=OptionAlpha API Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$WORK_DIR
Environment="PATH=$WORK_DIR/venv/bin:/usr/local/bin:/usr/bin"
ExecStart=$PYTHON_PATH -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable option-tracker
sudo systemctl start option-tracker

echo ""
echo "========================================="
echo "  部署完成！"
echo "========================================="
echo ""
echo "服务状态:"
sudo systemctl status option-tracker --no-pager
echo ""
echo "API地址: http://$(curl -s ifconfig.me):8000"
echo "API文档: http://$(curl -s ifconfig.me):8000/docs"
echo ""
echo "常用命令:"
echo "  查看日志: sudo journalctl -u option-tracker -f"
echo "  重启服务: sudo systemctl restart option-tracker"
echo "  停止服务: sudo systemctl stop option-tracker"
echo ""
echo "下一步:"
echo "1. 开放防火墙端口: sudo iptables -I INPUT -p tcp --dport 8000 -j ACCEPT"
echo "2. （可选）安装Nginx反向代理"
echo "3. 修改前端API地址为: http://$(curl -s ifconfig.me):8000/api/v1"
echo ""
