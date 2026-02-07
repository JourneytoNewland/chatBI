#!/bin/bash
# 监控服务启动脚本

set -e

echo "=========================================="
echo "chatBI 监控系统启动"
echo "=========================================="
echo ""

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker Desktop"
    exit 1
fi

# 启动监控服务
echo "🔄 启动监控服务..."
docker compose up -d prometheus grafana

# 等待服务就绪
echo "⏳ 等待服务就绪..."
sleep 5

# 检查服务状态
echo ""
echo "📊 服务状态:"
docker compose ps prometheus grafana

echo ""
echo "=========================================="
echo "✅ 监控服务启动完成"
echo "=========================================="
echo ""
echo "🔗 访问地址:"
echo "   Prometheus: http://localhost:9090"
echo "   Grafana:    http://localhost:3000"
echo "   用户名: admin"
echo "   密码:   admin"
echo ""
echo "💡 查看日志:"
echo "   docker compose logs -f prometheus"
echo "   docker compose logs -f grafana"
echo ""
