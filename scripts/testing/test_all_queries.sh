#!/bin/bash

echo "======================================"
echo "  智能问数系统 - 自动测试脚本"
echo "======================================"
echo ""

# 等待API就绪
echo "⏳ 等待API服务就绪..."
MAX_WAIT=120  # 最多等待2分钟
WAITED=0

while [ $WAITED -lt $MAX_WAIT ]; do
    # 尝试连接API
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo "✅ API服务已就绪!"
        break
    fi

    WAITED=$((WAITED + 5))
    echo "   等待中... ($WAITED/$MAX_WAIT 秒)"
    sleep 5
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "❌ API服务未能在 $MAX_WAIT 秒内启动"
    exit 1
fi

echo ""
echo "======================================"
echo "  开始测试所有查询案例"
echo "======================================"
echo ""

# 测试案例数组
QUERIES=(
    "最近7天的GMV"
    "本月按渠道统计DAU"
    "2024年1月的订单转化率"
)

# 结果文件
RESULT_FILE="/tmp/test_results_$(date +%Y%m%d_%H%M%S).json"
echo "[]" > "$RESULT_FILE"

TOTAL=0
PASSED=0
FAILED=0

# 测试每个查询
for i in "${!QUERIES[@]}"; do
    QUERY="${QUERIES[$i]}"
    TOTAL=$((TOTAL + 1))

    echo ""
    echo "----------------------------------------"
    echo "测试 $((i+1))/${#QUERIES[@]}: $QUERY"
    echo "----------------------------------------"

    # 调用API
    RESPONSE=$(curl -s -X POST http://localhost:8000/api/v2/query \
        -H 'Content-Type: application/json' \
        -d "{\"query\":\"$QUERY\"}" \
        --max-time 60)

    # 检查是否成功
    if echo "$RESPONSE" | grep -q '"intent"'; then
        echo "✅ 查询成功"

        # 提取关键信息
        CORE_QUERY=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('intent', {}).get('core_query', 'N/A'))" 2>/dev/null)
        SOURCE_LAYER=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('source_layer', 'N/A'))" 2>/dev/null)
        EXEC_TIME=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('execution_time_ms', 0))" 2>/dev/null)

        echo "   核心查询: $CORE_QUERY"
        echo "   来源层: $SOURCE_LAYER"
        echo "   耗时: ${EXEC_TIME}ms"

        PASSED=$((PASSED + 1))
    else
        echo "❌ 查询失败"
        echo "$RESPONSE" | head -100
        FAILED=$((FAILED + 1))
    fi

    # 保存响应
    python3 << EOF
import json

with open('$RESULT_FILE', 'r') as f:
    results = json.load(f)

try:
    response_data = json.loads('''$RESPONSE''')
    results.append({
        "query": "$QUERY",
        "success": "intent" in str(response_data),
        "response": response_data
    })
except:
    results.append({
        "query": "$QUERY",
        "success": False,
        "error": "Invalid JSON response"
    })

with open('$RESULT_FILE', 'w') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
EOF
done

echo ""
echo "======================================"
echo "  测试总结"
echo "======================================"
echo "总计: $TOTAL"
echo "通过: $PASSED"
echo "失败: $FAILED"
echo "成功率: $(( PASSED * 100 / TOTAL ))%"
echo ""
echo "详细结果已保存到: $RESULT_FILE"

if [ $PASSED -eq $TOTAL ]; then
    echo ""
    echo "🎉 所有测试通过！"
    exit 0
else
    echo ""
    echo "⚠️  部分测试失败"
    exit 1
fi
