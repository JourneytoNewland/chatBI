"""测试完整的查询流程."""

import sys
sys.path.append('/Users/wangzheng/Downloads/playDemo/AntigravityDemo/chatBI')

from src.api.complete_query import complete_query
from src.api.models import SearchRequest

print("=" * 70)
print("🔍 测试完整查询流程")
print("=" * 70)

# 创建请求
request = SearchRequest(query="为什么GMV最近下降了？")

print(f"\n查询: {request.query}")

try:
    result = complete_query(request)
    print(f"\n✅ 查询成功")
    print(f"   - 成功: {result.success}")
    print(f"   - 数据条数: {len(result.data) if result.data else 0}")

    if result.intent_info:
        intent = result.intent_info.final_intent
        print(f"   - 核心查询: {intent.core_query}")
        print(f"   - 趋势类型: {intent.trend_type}")

    if result.result and hasattr(result.result, 'root_cause_analysis'):
        print(f"   - 根因分析: {result.result.root_cause_analysis is not None}")

    if result.error:
        print(f"   - 错误信息: {result.error}")

except Exception as e:
    print(f"\n❌ 查询失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
