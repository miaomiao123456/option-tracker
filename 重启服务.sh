#!/bin/bash

echo "正在查找并停止现有服务..."
pkill -f "uvicorn main:app" || pkill -f "python main.py"
sleep 2

echo "正在启动服务..."
cd /Users/pm/Documents/期权交易策略/option_tracker
nohup python main.py > server.log 2>&1 &

sleep 3
echo "服务已启动!"
echo "访问地址:"
echo "  V3分析页面: http://localhost:8000/v3_analysis.html"
echo "  原前端页面: http://localhost:8000/frontend.html"
echo "  API文档:    http://localhost:8000/docs"
echo ""
echo "查看日志: tail -f /Users/pm/Documents/期权交易策略/option_tracker/server.log"
