#!/bin/bash

# 期权交易策略系统 - 阿里云自动部署脚本
# 用途: 自动打包并部署到阿里云服务器

set -e  # 遇到错误立即退出

# 配置
SERVER_IP="120.27.159.14"
SERVER_USER="root"
DEPLOY_DIR="/opt/option-tracker"
LOCAL_DIR="/Users/pm/Documents/期权交易策略/option_tracker"
TEMP_PACKAGE="/tmp/deploy_fixed.tar.gz"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== 期权交易策略系统 - 阿里云部署 ===${NC}\n"

# 步骤1: 打包
echo -e "${YELLOW}[步骤 1/4]${NC} 正在打包项目文件..."
cd "$LOCAL_DIR"

# 排除不需要的文件
tar -czf "$TEMP_PACKAGE" \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='*.log' \
    --exclude='backup_*.db' \
    --exclude='debug_screenshots' \
    --exclude='.netlify' \
    --exclude='.claude' \
    --exclude='frontend_backup*.html' \
    .

PACKAGE_SIZE=$(du -h "$TEMP_PACKAGE" | cut -f1)
echo -e "${GREEN}✓${NC} 打包完成，大小: ${PACKAGE_SIZE}"

# 步骤2: 上传文件
echo -e "\n${YELLOW}[步骤 2/4]${NC} 正在上传到服务器..."
scp "$TEMP_PACKAGE" "${SERVER_USER}@${SERVER_IP}:/tmp/"
echo -e "${GREEN}✓${NC} 上传完成"

# 步骤3: 服务器部署
echo -e "\n${YELLOW}[步骤 3/4]${NC} 正在服务器上部署..."
ssh "${SERVER_USER}@${SERVER_IP}" << 'ENDSSH'
    echo "停止旧服务..."
    pkill -f uvicorn || true

    echo "清理旧文件..."
    rm -rf /opt/option-tracker/*

    echo "解压新文件..."
    cd /opt/option-tracker
    tar -xzf /tmp/deploy_fixed.tar.gz

    echo "启动服务..."
    nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 80 > app.log 2>&1 &

    echo "等待服务启动..."
    sleep 5

    echo "验证服务状态..."
    curl -s http://localhost/health || echo "警告: 健康检查失败"
ENDSSH

echo -e "${GREEN}✓${NC} 部署完成"

# 步骤4: 验证
echo -e "\n${YELLOW}[步骤 4/4]${NC} 验证部署..."

# 测试健康检查
echo -n "测试健康检查..."
HEALTH_CHECK=$(curl -s "http://${SERVER_IP}/health" || echo "failed")
if [[ "$HEALTH_CHECK" == *"ok"* ]]; then
    echo -e " ${GREEN}✓${NC}"
else
    echo -e " ${RED}✗${NC}"
    echo "警告: 健康检查失败，请检查服务日志"
fi

# 测试前端页面
echo -n "测试前端页面..."
FRONTEND_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "http://${SERVER_IP}/frontend")
if [[ "$FRONTEND_CHECK" == "200" ]]; then
    echo -e " ${GREEN}✓${NC}"
else
    echo -e " ${RED}✗${NC}"
    echo "警告: 前端页面访问失败 (HTTP $FRONTEND_CHECK)"
fi

# 完成
echo -e "\n${GREEN}=== 部署完成 ===${NC}"
echo ""
echo "访问地址: http://${SERVER_IP}/frontend"
echo "API文档:  http://${SERVER_IP}/docs"
echo ""
echo "查看日志: ssh ${SERVER_USER}@${SERVER_IP} 'tail -f ${DEPLOY_DIR}/app.log'"
echo "查看进程: ssh ${SERVER_USER}@${SERVER_IP} 'ps aux | grep uvicorn'"
echo ""
echo -e "${YELLOW}提示:${NC} 如果页面无法访问，请检查:"
echo "  1. 防火墙是否开放80端口"
echo "  2. 服务器上的Python环境是否正常"
echo "  3. 查看服务器日志排查错误"
