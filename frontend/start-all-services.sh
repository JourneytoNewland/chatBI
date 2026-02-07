#!/bin/bash

# 智能问数系统 - 快速启动脚本

echo "🚀 启动智能问数系统..."
echo ""

# 检查并停止旧进程
echo "🔍 检查旧进程..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:8080 | xargs kill -9 2>/dev/null
sleep 2

# 启动后端服务
echo "📡 启动后端服务 (端口 8000)..."
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > /tmp/uvicorn.log 2>&1 &
BACKEND_PID=$!
echo "   后端 PID: $BACKEND_PID"

# 等待后端启动
sleep 5

# 检查后端健康状态
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo "   ✅ 后端服务启动成功"
else
    echo "   ❌ 后端服务启动失败"
    cat /tmp/uvicorn.log
    exit 1
fi

# 启动前端服务
echo "🌐 启动前端服务 (端口 8080)..."
cd frontend
python -m http.server 8080 > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "   前端 PID: $FRONTEND_PID"

sleep 2

# 检查前端服务
if curl -s http://localhost:8080/ | grep -q "DOCTYPE"; then
    echo "   ✅ 前端服务启动成功"
else
    echo "   ❌ 前端服务启动失败"
fi

echo ""
echo "======================================"
echo "  🎉 系统启动完成！"
echo "======================================"
echo ""
echo "📍 访问地址:"
echo "   前端界面: http://localhost:8080"
echo "   后端 API:  http://localhost:8000"
echo "   API 文档:  http://localhost:8000/docs"
echo ""
echo "📋 进程信息:"
echo "   后端 PID: $BACKEND_PID"
echo "   前端 PID: $FRONTEND_PID"
echo ""
echo "🛑 停止服务:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo "   或运行: ./stop-all-services.sh"
echo "======================================"

# 保存 PID 到文件
echo "$BACKEND_PID" > /tmp/backend.pid
echo "$FRONTEND_PID" > /tmp/frontend.pid
