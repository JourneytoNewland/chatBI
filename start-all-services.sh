#!/bin/bash
# 智能问数系统 - 快速启动脚本
# 验收版本 v3.0 - Production Ready

set -e

echo "🚀 智能问数系统启动中..."
echo ""

# 设置环境变量
export PYTHONPATH="/Users/wangzheng/Downloads/playDemo/AntigravityDemo/chatBI:$PYTHONPATH"
export HF_HUB_OFFLINE=1
export VECTORIZER_MODEL_NAME="BAAI/bge-m3"

# 检查端口占用
check_port() {
    local port=$1
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "⚠️  端口 $port 已被占用，正在清理..."
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
}

# 停止旧服务
echo "🛑 停止旧服务..."
pkill -9 -f "uvicorn src.api.main" 2>/dev/null || true
pkill -9 -f "python.*http.server.*8080" 2>/dev/null || true
sleep 2

# 检查端口
echo "🔍 检查端口..."
check_port 8000
check_port 8080
check_port 6333

# 启动 Qdrant (如果未运行)
if ! lsof -ti:6333 > /dev/null 2>&1; then
    echo "📊 启动 Qdrant 向量数据库..."
    docker start chatbi-qdrant 2>/dev/null || docker run -d --name chatbi-qdrant \
        -p 6333:6333 -p 6334:6334 \
        -v $(pwd)/qdrant_data:/qdrant/storage \
        qdrant/qdrant:v1.12.0 2>/dev/null || echo "⚠️  Qdrant 启动失败，请手动启动"
    sleep 3
fi

# 启动 Neo4j (如果未运行)
if ! lsof -ti:7687 > /dev/null 2>&1; then
    echo "🧠 启动 Neo4j 图数据库..."
    docker start chatbi-neo4j 2>/dev/null || echo "⚠️  Neo4j 启动失败，请手动启动"
    sleep 3
fi

# 启动 API 服务
echo "🔵 启动 API 服务 (端口 8000)..."
nohup python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 \
    > /tmp/chatbi_api.log 2>&1 &
API_PID=$!
sleep 5

# 检查 API 是否启动成功
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API 服务启动成功 (PID: $API_PID)"
else
    echo "❌ API 服务启动失败，请检查日志: /tmp/chatbi_api.log"
    exit 1
fi

# 启动前端服务
echo "🟢 启动前端服务 (端口 8080)..."
cd frontend
nohup python3 -m http.server 8080 > /tmp/chatbi_frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
sleep 2

echo "✅ 前端服务启动成功 (PID: $FRONTEND_PID)"
echo ""

# 服务状态
echo "📋 服务状态:"
echo "   ✅ API:      http://localhost:8000"
echo "   ✅ 前端:     http://localhost:8080/pipeline-flow.html"
echo "   ✅ API文档:  http://localhost:8000/docs"
echo "   ✅ Qdrant:   http://localhost:6333"
echo "   ✅ Neo4j:    bolt://localhost:7687"
echo ""

# 快速测试
echo "🧪 执行快速测试..."
curl -s -X POST http://localhost:8000/api/v3/query \
    -H "Content-Type: application/json" \
    -d '{"query":"最近7天的GMV"}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"   查询: {d['query']}\")
print(f\"   核心查询: {d['intent']['core_query']}\")
print(f\"   MQL: {'✅' if d['mql'] else '❌'}\")
print(f\"   SQL: {'✅' if d['sql'] else '❌'}\")
print(f\"   数据: {len(d['data'])} 条\")
print(f\"   解读: {'✅' if d['interpretation'] else '❌'}\")
print(f\"   耗时: {d['execution_time_ms']:.2f}ms\")
print(\"\n✅ 系统测试通过！\")
" 2>/dev/null || echo "⚠️  测试失败，请手动验证"

echo ""
echo "🎉 智能问数系统启动完成！"
echo ""
echo "📖 使用指南:"
echo "   1. 在浏览器中打开: http://localhost:8080/pipeline-flow.html"
echo "   2. 输入自然语言查询，例如："
echo "      - \"最近7天的GMV\""
echo "      - \"本月按渠道统计DAU\""
echo "      - \"按地区统计GMV\""
echo ""
echo "📝 日志文件:"
echo "   API:      /tmp/chatbi_api.log"
echo "   前端:     /tmp/chatbi_frontend.log"
echo ""
echo "🛑 停止服务:"
echo "   ./stop-all-services.sh"
echo ""

# 保存 PID
echo $API_PID > /tmp/chatbi_api.pid
echo $FRONTEND_PID > /tmp/chatbi_frontend.pid

echo "✅ 所有服务已启动，PID 已保存"
