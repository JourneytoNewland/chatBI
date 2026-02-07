#!/bin/bash
# 性能基准测试启动脚本

set -e

echo "=========================================="
echo "chatBI 性能基准测试"
echo "=========================================="
echo ""

# 检查服务是否运行
echo "📡 检查服务状态..."
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ 服务未运行，请先启动服务:"
    echo "   python run-production-server.py"
    echo "   或"
    echo "   bash run_demo.sh"
    exit 1
fi

echo "✅ 服务正常运行"
echo ""

# 创建结果目录
mkdir -p tests/performance/results

# 运行Python基准测试
echo "🔄 运行性能基准测试..."
echo ""

python tests/performance/benchmark.py http://localhost:8000

echo ""
echo "=========================================="
echo "✅ 性能基准测试完成"
echo "=========================================="
echo ""
echo "📊 结果文件位置: tests/performance/results/"
echo ""
echo "💡 运行Locust压力测试:"
echo "   locust -f tests/performance/load_test.py --host=http://localhost:8000"
echo ""
