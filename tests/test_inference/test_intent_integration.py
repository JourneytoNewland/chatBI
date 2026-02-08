"""测试完整的意图识别流程."""

import sys
sys.path.append('/Users/wangzheng/Downloads/playDemo/AntigravityDemo/chatBI')

from src.inference.intent import IntentRecognizer

print("=" * 70)
print("🔍 诊断意图识别流程")
print("=" * 70)

# 创建意图识别器
recognizer = IntentRecognizer()

# 测试查询
query = "为什么GMV最近下降了？"
print(f"\n原始查询: {query}")

try:
    intent = recognizer.recognize(query)
    print(f"✅ 意图识别成功")
    print(f"   - core_query: {intent.core_query}")
    print(f"   - query: {intent.query}")
    print(f"   - time_range: {intent.time_range}")
    print(f"   - trend_type: {intent.trend_type}")
    print(f"   - 维度: {intent.dimensions}")
    print(f"   - 聚合: {intent.aggregation_type}")

    # 检查是否有None值
    print(f"\n✅ 检查None值:")
    print(f"   - core_query is None: {intent.core_query is None}")
    print(f"   - query is None: {intent.query is None}")

except Exception as e:
    print(f"❌ 意图识别失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
