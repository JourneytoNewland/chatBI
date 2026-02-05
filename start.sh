#!/bin/bash

echo "🚀 启动智能问数系统 v3.0"
echo "=================================="

# 启动前端服务
echo ""
echo "📱 启动前端服务..."
cd frontend
python -m http.server 8080 > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ 前端服务已启动 (PID: $FRONTEND_PID)"
echo "   访问地址: http://localhost:8080/index_v3.html"
cd ..

# 启动后端API服务
echo ""
echo "🔧 启动后端API服务..."
python -m uvicorn src.api.v2_query_api:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level warning \
    > /tmp/api_server.log 2>&1 &
API_PID=$!
echo "✅ API服务已启动 (PID: $API_PID)"
echo "   API地址: http://localhost:8000"
echo "   API文档: http://localhost:8000/docs"

echo ""
echo "=================================="
echo "⏳ 服务正在启动，模型加载中（约30-60秒）"
echo ""
echo "📊 访问地址："
echo "   前端页面: http://localhost:8080/index_v3.html"
echo "   API文档: http://localhost:8000/docs"
echo ""
echo "📝 查看日志："
echo "   tail -f /tmp/api_server.log"
echo ""
echo "🛑 停止服务："
echo "   pkill -f 'http.server'"
echo "   pkill -f 'uvicorn'"
echo "=================================="
