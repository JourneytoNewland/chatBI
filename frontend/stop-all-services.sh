#!/bin/bash

# 智能问数系统 - 快速停止脚本

echo "🛑 停止智能问数系统..."
echo ""

# 从 PID 文件读取
if [ -f /tmp/backend.pid ]; then
    BACKEND_PID=$(cat /tmp/backend.pid)
    kill $BACKEND_PID 2>/dev/null
    echo "✅ 后端服务已停止 (PID: $BACKEND_PID)"
    rm /tmp/backend.pid
fi

if [ -f /tmp/frontend.pid ]; then
    FRONTEND_PID=$(cat /tmp/frontend.pid)
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ 前端服务已停止 (PID: $FRONTEND_PID)"
    rm /tmp/frontend.pid
fi

# 强制清理端口
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:8080 | xargs kill -9 2>/dev/null

echo ""
echo "✅ 所有服务已停止"
