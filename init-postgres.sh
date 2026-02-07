#!/bin/bash
# PostgreSQL 数据库初始化脚本

set -e

echo "=========================================="
echo "chatBI PostgreSQL 数据库初始化"
echo "=========================================="
echo ""

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker Desktop"
    exit 1
fi

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件，从 .env.example 复制..."
    cp .env.example .env
    echo "✅ .env 文件已创建"
fi

# 启动 PostgreSQL 容器
echo "🔄 启动 PostgreSQL 容器..."
docker compose up -d postgres

# 等待 PostgreSQL 就绪
echo "⏳ 等待 PostgreSQL 就绪..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker exec chatbi-postgres pg_isready -U chatbi -d chatbi > /dev/null 2>&1; then
        echo "✅ PostgreSQL 已就绪"
        break
    fi
    attempt=$((attempt + 1))
    echo "  等待中... ($attempt/$max_attempts)"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ PostgreSQL 启动超时"
    exit 1
fi

# 运行数据库迁移
echo ""
echo "🔄 运行数据库迁移..."
python -m src.database.run_migration

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 数据库迁移完成"
else
    echo ""
    echo "❌ 数据库迁移失败"
    exit 1
fi

# 初始化测试数据
echo ""
echo "🔄 初始化测试数据..."
python -m src.database.init_test_data

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ PostgreSQL 初始化完成！"
    echo "=========================================="
    echo ""
    echo "📊 数据库信息："
    echo "   - Host: localhost:5432"
    echo "   - Database: chatbi"
    echo "   - User: chatbi"
    echo "   - Password: chatbi_password"
    echo ""
    echo "💡 快速连接："
    echo "   docker exec -it chatbi-postgres psql -U chatbi -d chatbi"
    echo ""
else
    echo ""
    echo "❌ 测试数据初始化失败"
    exit 1
fi
