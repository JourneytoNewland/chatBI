"""测试根因分析模块."""

import sys
sys.path.append('/Users/wangzheng/Downloads/playDemo/AntigravityDemo/chatBI')

from src.inference.root_cause.root_cause_analyzer import RootCauseAnalyzer
from src.inference.intent import QueryIntent

# 创建测试数据（GMV下降场景）
test_data_gmv = [
    {"date": "2026-02-01", "value": 50000, "地区": "华东", "品类": "电子产品", "渠道": "线上"},
    {"date": "2026-02-02", "value": 48000, "地区": "华东", "品类": "电子产品", "渠道": "线上"},
    {"date": "2026-02-03", "value": 52000, "地区": "华东", "品类": "电子产品", "渠道": "线上"},
    {"date": "2026-02-04", "value": 35000, "地区": "华东", "品类": "电子产品", "渠道": "线上"},  # 异常下降
    {"date": "2026-02-05", "value": 30000, "地区": "华东", "品类": "电子产品", "渠道": "线上"},  # 异常下降
    {"date": "2026-02-06", "value": 32000, "地区": "华东", "品类": "电子产品", "渠道": "线上"},
    {"date": "2026-02-07", "value": 31000, "地区": "华东", "品类": "电子产品", "渠道": "线上"},
]

# 创建测试意图
intent = QueryIntent(
    query="为什么GMV下降了？",
    core_query="GMV",
    time_range=None,
    time_granularity=None,
    aggregation_type=None,
    dimensions=[],
    comparison_type=None,
    filters={}
)

# 创建根因分析器
analyzer = RootCauseAnalyzer()

# 执行分析
print("=" * 60)
print("📊 测试用例1: GMV下降分析")
print("=" * 60)

result = analyzer.analyze(
    query="为什么GMV最近下降了？",
    intent=intent,
    data=test_data_gmv,
    dimensions_to_analyze=["地区", "品类", "渠道"]
)

print(f"\n✅ 分析完成!")
print(f"   - 异常数量: {len(result.anomalies)}")
print(f"   - 维度数量: {len(result.dimensions)}")
print(f"   - 趋势类型: {result.trends.trend_type}")
print(f"   - 因果因素: {len(result.causal_factors)}")
print(f"   - 建议数量: {len(result.recommendations)}")

print("\n📋 分析报告:")
print("-" * 60)
print(result.report)
print("-" * 60)

if result.anomalies:
    print("\n⚠️  异常详情:")
    for anomaly in result.anomalies[:3]:
        print(f"   - {anomaly.timestamp}: {anomaly.type} (偏离{anomaly.deviation_pct:.1f}%)")

if result.causal_factors:
    print("\n🔗 因果因素:")
    for factor in result.causal_factors[:3]:
        print(f"   - {factor.name}: {factor.explanation} (置信度: {factor.confidence:.0%})")

if result.recommendations:
    print("\n💡 行动建议:")
    for rec in result.recommendations:
        print(f"   - {rec}")

print("\n" + "=" * 60)

# 测试用例2: DAU增长
print("\n📊 测试用例2: DAU异常增长分析")
print("=" * 60)

test_data_dau = [
    {"date": "2026-02-01", "value": 10000, "地区": "华东", "渠道": "线上"},
    {"date": "2026-02-02", "value": 10500, "地区": "华东", "渠道": "线上"},
    {"date": "2026-02-03", "value": 11000, "地区": "华东", "渠道": "线上"},
    {"date": "2026-02-04", "value": 15000, "地区": "华东", "渠道": "线上"},  # 异常增长
    {"date": "2026-02-05", "value": 18000, "地区": "华东", "渠道": "线上"},  # 异常增长
    {"date": "2026-02-06", "value": 17500, "地区": "华东", "渠道": "线上"},
    {"date": "2026-02-07", "value": 19000, "地区": "华东", "渠道": "线上"},
]

intent_dau = QueryIntent(
    query="为什么DAU突然增长了？",
    core_query="DAU",
    time_range=None,
    time_granularity=None,
    aggregation_type=None,
    dimensions=[],
    comparison_type=None,
    filters={}
)

result_dau = analyzer.analyze(
    query="为什么DAU突然增长了？",
    intent=intent_dau,
    data=test_data_dau,
    dimensions_to_analyze=["地区", "渠道"]
)

print(f"\n✅ 分析完成!")
print(f"   - 异常数量: {len(result_dau.anomalies)}")
print(f"   - 维度数量: {len(result_dau.dimensions)}")
print(f"   - 趋势类型: {result_dau.trends.trend_type}")
print(f"   - 因果因素: {len(result_dau.causal_factors)}")

print("\n📋 分析报告:")
print("-" * 60)
print(result_dau.report)
print("-" * 60)

if result_dau.causal_factors:
    print("\n🔗 因果因素:")
    for factor in result_dau.causal_factors[:3]:
        print(f"   - {factor.name}: {factor.explanation} (置信度: {factor.confidence:.0%})")

print("\n" + "=" * 60)
print("✅ 所有测试用例完成!")
