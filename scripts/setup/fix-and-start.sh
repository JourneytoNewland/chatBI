#!/bin/bash
# Docker 配置完成后的验证和启动脚本

echo "=== 🚀 启动智能问数系统 ==="
echo ""

DOCKER="/Applications/Docker.app/Contents/Resources/bin/docker"

echo "⏳ 等待 Docker 重启完成..."
echo "（如果你还没有重启 Docker，请先执行以下步骤：）"
echo ""
echo "1. 打开 Docker Desktop"
echo "2. Settings → Docker Engine"
echo "3. 粘贴以下配置："
echo ""
cat ~/.docker/daemon.json
echo ""
echo "4. 点击 'Apply & Restart'"
echo "5. 等待 30 秒后，按回车继续..."
echo ""
read -p "按回车键继续..."

echo ""
echo "=== 测试 Docker ==="
echo "正在拉取测试镜像..."

$DOCKER pull alpine:latest > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Docker 正常！"
else
    echo "❌ Docker 仍有问题，请检查："
    echo "   - Docker Desktop 是否已重启？"
    echo "   - 网络连接是否正常？"
    echo "   - 是否需要配置代理？"
    exit 1
fi

echo ""
echo "=== 启动数据库服务 ==="
echo "1️⃣ 拉取 Qdrant 镜像..."
$DOCKER pull qdrant/qdrant:v1.7.4

echo ""
echo "2️⃣ 拉取 Neo4j 镜像..."
$DOCKER pull neo4j:5.15-community

echo ""
echo "3️⃣ 启动服务..."
docker compose up -d

echo ""
echo "=== 等待服务启动 ==="
sleep 10

echo ""
echo "=== 检查服务状态 ==="
docker compose ps

echo ""
echo "=== 初始化数据 ==="
echo "安装 Python 依赖..."
source .venv/bin/activate
pip install -e . -q

echo ""
echo "初始化向量数据..."
python scripts/init_seed_data.py

echo ""
echo "初始化图谱数据..."
python scripts/init_graph.py

echo ""
echo "=== 🎉 启动完成！==="
echo ""
echo "服务地址："
echo "  - API:     http://localhost:8000"
echo "  - Qdrant:  http://localhost:6333"
echo "  - Neo4j:   http://localhost:7474"
echo "  - 前端:    打开 frontend/index.html"
echo ""
echo "启动后端服务："
echo "  source .venv/bin/activate"
echo "  uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
