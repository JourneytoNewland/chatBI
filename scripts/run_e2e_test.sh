#!/bin/bash

# 清理端口
lsof -ti:8000 | xargs kill -9 2>/dev/null
sleep 2

# 启动服务
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > /tmp/uvicorn_test.log 2>&1 &
sleep 8

# 运行测试
echo "========================================"
echo "🧪 运行完整端到端测试"
echo "========================================"
python scripts/test_e2e.py
TEST_RESULT=$?

# 停止服务
echo ""
echo "========================================"
echo "🛑 停止服务"
echo "========================================"
lsof -ti:8000 | xargs kill -9 2>/dev/null
wait

# 显示日志摘要
echo ""
echo "========================================"
echo "📋 服务日志（最后 30 行）"
echo "========================================"
tail -30 /tmp/uvicorn_test.log

exit $TEST_RESULT
