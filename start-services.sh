#!/bin/bash
# chatBI 一键启动脚本

set -e

echo "=========================================="
echo "chatBI 一键启动"
echo "=========================================="
echo ""

cd /Users/wangzheng/Downloads/playDemo/AntigravityDemo/chatBI
source .venv/bin/activate

# 1. 检查并清理端口
echo "1️⃣ 检查端口..."
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "   端口8000已占用，正在释放..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi
echo "   ✅ 端口8000已就绪"
echo ""

# 2. 启动API服务
echo "2️⃣ 启动API服务..."
nohup python -m uvicorn src.api.main:app --host localhost --port 8000 > /tmp/chatbi_api.log 2>&1 &
API_PID=$!
echo "   ✅ API服务已启动 (PID: $API_PID)"
echo $API_PID > /tmp/chatbi_api.pid

# 3. 等待服务就绪
echo ""
echo "3️⃣ 等待服务就绪..."
echo "   （首次启动需要加载BGE-M3模型，约10-20秒）"
echo ""

for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "   ✅ 服务就绪！"
        break
    fi
    printf "   等待中... (%02d/30)\r" $i
    sleep 1
done

echo ""
echo "=========================================="
echo "✅ chatBI 启动完成！"
echo "=========================================="
echo ""
echo "📡 服务地址："
echo "   🌐 API文档:     http://localhost:8000/docs"
echo "   🌐 前端界面:   在浏览器打开 frontend/index.html"
echo ""
echo "🧪 快速测试："
echo "   curl -X POST http://localhost:8000/api/v3/query \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"query\": \"最近7天GMV\"}'"
echo ""
echo "💡 管理命令："
echo "   查看日志: tail -f /tmp/chatbi_api.log"
echo "   停止服务: kill $API_PID"
echo "   重启服务: bash $0"
echo ""
echo "📖 更多文档："
echo "   - 主README: cat README.md"
echo "   - 快速测试: cat QUICKSTART_TEST.md"
echo "   - 项目结构: cat docs/PROJECT_STRUCTURE.md"
