#!/bin/bash
# 超级简单部署脚本 - 无需GitHub，直接部署到 Render

echo "========================================="
echo "  期权交易跟踪器 - 本地直接部署方案"
echo "========================================="
echo ""

# 检查是否安装了必要工具
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装"
    exit 1
fi

echo "✅ Python3 已安装"
echo ""

# 安装依赖
echo "📦 安装项目依赖..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败"
    exit 1
fi

echo "✅ 依赖安装完成"
echo ""

# 检查环境变量
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件，创建中..."
    cat > .env << 'EOF'
DATABASE_URL=sqlite:///./option_tracker.db
JYK_USER=18321399574
JYK_PASS=yi2013405
GEMINI_API_KEY=sk-IJhu2VBNt2G97XJeE6F82dD8047c4a2989326250068aA1F5
GEMINI_BASE_URL=https://www.apillm.online/v1
DEBUG=false
LOG_LEVEL=INFO
EOF
    echo "✅ .env 文件已创建"
fi

echo ""
echo "========================================="
echo "  启动本地服务"
echo "========================================="
echo ""
echo "API 将运行在: http://localhost:8000"
echo "API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

# 启动服务
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
