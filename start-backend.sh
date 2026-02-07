#!/bin/bash
# 启动后端服务

export PYTHONPATH="/Users/wangzheng/Downloads/playDemo/AntigravityDemo/chatBI:$PYTHONPATH"
cd /Users/wangzheng/Downloads/playDemo/AntigravityDemo/chatBI

echo "=== 🚀 启动后端服务 ==="
echo ""
echo "📡 服务地址: http://localhost:8000"
echo "📖 API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

source .venv/bin/activate
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
