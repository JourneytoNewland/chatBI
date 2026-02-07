#!/bin/bash
# 演示服务器启动脚本

export PYTHONPATH="/Users/wangzheng/Downloads/playDemo/AntigravityDemo/chatBI:$PYTHONPATH"
source /Users/wangzheng/Downloads/playDemo/AntigravityDemo/chatBI/.venv/bin/activate

cd /Users/wangzheng/Downloads/playDemo/AntigravityDemo/chatBI

echo "🚀 启动智能问数系统（演示模式）"
echo ""
echo "📡 服务地址："
echo "   - API:     http://localhost:8000"
echo "   - 文档:    http://localhost:8000/docs"
echo "   - 前端:    在浏览器中打开 frontend/index.html"
echo ""
echo "✅ 服务器启动中..."
echo ""

python -m uvicorn scripts.run_demo_server:app --host 0.0.0.0 --port 8000
