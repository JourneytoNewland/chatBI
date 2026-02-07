#!/bin/bash
# 智能问数系统 - Docker 启动脚本

set -e

echo "🚀 启动智能问数系统（Docker 模式）"
echo "================================"
echo ""

# 1. 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker Desktop"
    exit 1
fi

# 2. 检查 Docker Compose
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose 未可用，请升级 Docker Desktop"
    exit 1
fi

# 3. 启动 Docker 服务
echo "📦 启动 Docker 服务（Qdrant + Neo4j）..."
docker compose up -d

echo ""
echo "⏳ 等待服务启动..."
sleep 5

# 4. 检查服务状态
echo ""
echo "✅ 检查服务状态..."
docker compose ps

# 5. 显示服务信息
echo ""
echo "================================"
echo "🎯 服务地址："
echo "  - Qdrant:    http://localhost:6333"
echo "  - Qdrant Dashboard: http://localhost:6333/dashboard"
echo "  - Neo4j:     http://localhost:7474"
echo "    用户名: neo4j"
echo "    密码:   password"
echo ""
echo "================================"
echo "📝 下一步操作："
echo ""
echo "1️⃣  安装 Python 依赖（首次运行）："
echo "   python3 -m venv .venv"
echo "   source .venv/bin/activate"
echo "   pip install -e ."
echo ""
echo "2️⃣  初始化数据（首次运行）："
echo "   python scripts/init_seed_data.py"
echo "   python scripts/init_graph.py"
echo ""
echo "3️⃣  启动后端 API："
echo "   source .venv/bin/activate"
echo "   uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "4️⃣  打开前端界面："
echo "   在浏览器中打开 frontend/index.html"
echo ""
echo "================================"
echo "🛑 停止服务："
echo "   docker compose down"
echo "================================"
