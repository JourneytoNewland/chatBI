#!/bin/bash
# chatBI 系统状态快速检查脚本

echo "=========================================="
echo "chatBI 系统状态检查"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 检查API服务状态
echo "1️⃣  API服务状态"
if [ -f /tmp/chatbi_api.pid ]; then
    PID=$(cat /tmp/chatbi_api.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "   ${GREEN}✅ 运行中${NC} (PID: $PID)"
    else
        echo -e "   ${RED}❌ 未运行${NC} (PID $PID 已停止)"
    fi
else
    echo -e "   ${YELLOW}⚠️  未启动${NC} (无PID文件)"
fi
echo ""

# 2. 健康检查
echo "2️⃣  健康检查"
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health 2>/dev/null)
if [ $? -eq 0 ]; then
    echo -e "   ${GREEN}✅ 通过${NC}"
    echo "   响应: $HEALTH_RESPONSE"
else
    echo -e "   ${RED}❌ 失败${NC} (无法连接到API服务)"
fi
echo ""

# 3. 测试查询API
echo "3️⃣  查询API测试"
QUERY_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v3/query \
    -H "Content-Type: application/json" \
    -d '{"query": "最近7天GMV"}' 2>/dev/null)

if [ $? -eq 0 ] && echo "$QUERY_RESPONSE" | grep -q '"intent"'; then
    echo -e "   ${GREEN}✅ 正常${NC}"

    # 提取关键信息
    CORE_QUERY=$(echo "$QUERY_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['intent']['core_query'])" 2>/dev/null)
    EXECUTION_TIME=$(echo "$QUERY_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"{data['execution_time_ms']:.2f}ms\")" 2>/dev/null)
    DATA_COUNT=$(echo "$QUERY_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('data', [])))" 2>/dev/null)

    echo "   核心查询: $CORE_QUERY"
    echo "   执行时间: $EXECUTION_TIME"
    echo "   数据条数: $DATA_COUNT"
else
    echo -e "   ${RED}❌ 失败${NC} (查询API返回错误)"
fi
echo ""

# 4. 前端文件检查
echo "4️⃣  前端文件"
if [ -f "frontend/index.html" ]; then
    FILE_SIZE=$(ls -lh frontend/index.html | awk '{print $5}')
    echo -e "   ${GREEN}✅ 存在${NC} (大小: $FILE_SIZE)"
else
    echo -e "   ${RED}❌ 缺失${NC} (frontend/index.html 不存在)"
fi
echo ""

# 5. 日志文件
echo "5️⃣  日志文件"
if [ -f /tmp/chatbi_api.log ]; then
    LOG_SIZE=$(ls -lh /tmp/chatbi_api.log | awk '{print $5}')
    LAST_LINE=$(tail -1 /tmp/chatbi_api.log 2>/dev/null)
    echo -e "   ${GREEN}✅ 存在${NC} (大小: $LOG_SIZE)"
    echo "   最后日志: ${LAST_LINE:0:80}..."
else
    echo -e "   ${YELLOW}⚠️  不存在${NC} (/tmp/chatbi_api.log)"
fi
echo ""

# 6. 总结
echo "=========================================="
echo "检查完成"
echo "=========================================="
echo ""
echo "💡 快速操作："
echo "   启动服务: bash start-services.sh"
echo "   查看日志: tail -f /tmp/chatbi_api.log"
echo "   打开前端: 在浏览器打开 frontend/index.html"
echo "   API文档: http://localhost:8000/docs"
echo ""
