#!/bin/bash
# 智能问数系统 - 本地模式启动脚本（无需 Docker）

set -e

echo "🚀 启动智能问数系统（本地模拟模式）"
echo "================================"
echo ""

# 1. 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 2. 创建虚拟环境
if [ ! -d ".venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv .venv
fi

# 3. 激活虚拟环境
echo "✅ 激活虚拟环境..."
source .venv/bin/activate

# 4. 安装依赖
echo "📥 安装依赖..."
pip install --upgrade pip -q
pip install fastapi uvicorn pydantic pydantic-settings python-dotenv -q

# 5. 创建简化版配置
cat > .env.local << 'EOF'
# 本地模式配置
QDRANT_HOST=localhost
QDRANT_PORT=6333
VECTORIZER_MODEL_NAME=m3e-base
VECTORIZER_DEVICE=cpu
DEBUG=true
LOG_LEVEL=INFO
EOF

echo ""
echo "================================"
echo "✅ 环境准备完成！"
echo ""
echo "🎯 启动方式："
echo ""
echo "方式 1 - 使用模拟数据（推荐测试）："
echo "  source .venv/bin/activate"
echo "  python scripts/run_demo_server.py"
echo ""
echo "方式 2 - 完整服务（需要 Docker）："
echo "  ./start-docker.sh"
echo "  source .venv/bin/activate"
echo "  python scripts/init_seed_data.py"
echo "  uvicorn src.api.main:app --reload"
echo ""
echo "================================"
