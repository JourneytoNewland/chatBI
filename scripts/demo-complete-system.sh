#!/bin/bash
# 智能问数系统完整演示

echo "=== 🚀 智能问数系统 v2.0 - 完整演示 ==="
echo ""
echo "📊 核心功能："
echo "  ✅ 25+ 指标体系（电商、用户、营收、营销、客服、增长）"
echo "  ✅ MQL自动生成（8种操作符）"
echo "  ✅ MQL执行引擎（模拟数据）"
echo "  ✅ 根因分析（4种分析类型）"
echo "  ✅ 图谱可视化管理"
echo "  ✅ 智谱AI GLM-4 集成"
echo ""
echo "📍 开始演示..."
echo ""

export PYTHONPATH="/Users/wangzheng/Downloads/playDemo/AntigravityDemo/chatBI:$PYTHONPATH"
source .venv/bin/activate

python << 'EOF'
import sys
sys.path.insert(0, "/Users/wangzheng/Downloads/playDemo/AntigravityDemo/chatBI")

print("\n" + "=" * 70)
print("演示1: 指标体系")
print("=" * 70)

from src.mql.metrics import registry

metrics = registry.get_all_metrics()
print(f"\n📊 指标总数: {len(metrics)}")
print(f"\n按业务域分类:")

for domain in ["电商", "用户", "营收", "营销", "客服", "增长"]:
    domain_metrics = registry.get_metrics_by_domain(domain)
    print(f"\n  {domain} ({len(domain_metrics)}个):")
    for m in domain_metrics:
        print(f"    - {m['name']} ({m['description']})")

print("\n" + "=" * 70)
print("演示2: MQL生成")
print("=" * 70)

from src.inference.intent import IntentRecognizer
from src.mql.generator import MQLGenerator

recognizer = IntentRecognizer()
generator = MQLGenerator()

test_queries = [
    "最近7天的GMV总和",
    "按地区的DAU",
    "本月营收同比",
    "转化率是多少"
]

for query in test_queries:
    print(f"\n查询: {query}")
    print("-" * 70)

    intent = recognizer.recognize(query)
    mql = generator.generate(intent)

    print(f"✅ 生成的MQL:")
    print(str(mql))

print("\n" + "=" * 70)
print("演示3: MQL执行")
print("=" * 70)

from src.mql.engine import MQLExecutionEngine
from datetime import datetime, timedelta
from src.mql.mql import MQLQuery, TimeRange, MetricOperator

engine = MQLExecutionEngine()

# 构建查询
query = MQLQuery(
    metric="GMV",
    operator=MetricOperator.SUM,
    time_range=TimeRange(
        start=datetime(2024, 1, 1),
        end=datetime(2024, 1, 7),
        granularity="day"
    )
)

print("\n执行查询:")
print(str(query))
print("\n结果:")

result = engine.execute(query)

print(f"  返回行数: {result['row_count']}")
print(f"  执行时间: {result['execution_time_ms']}ms")
print(f"  数据预览:")
for row in result['result'][:3]:
    print(f"    {row}")

print("\n" + "=" * 70)
print("演示4: 根因分析")
print("=" * 70)

from src.mql.root_cause import RootCauseAnalyzer

analyzer = RootCauseAnalyzer()

time_range = TimeRange(
    start=datetime.now() - timedelta(days=7),
    end=datetime.now(),
    granularity="day"
)

print("\n分析: GMV（最近7天，阈值10万）")
print("-" * 70)

root_causes = analyzer.analyze(
    metric="GMV",
    time_range=time_range,
    threshold=100000,
    dimensions=["地区", "品类"]
)

print(f"\n发现 {len(root_causes)} 个潜在根因:")
for i, cause in enumerate(root_causes[:3], 1):
    print(f"\n{i}. [{cause.severity.upper()}] {cause.cause_type}")
    print(f"   {cause.description}")
    if cause.suggestions:
        print(f"   💡 建议: {cause.suggestions[0]}")

print("\n" + "=" * 70)
print("✅ 演示完成！")
print("=" * 70)
print("\n🎯 核心优势:")
print("  1. 📊 完整指标体系 - 25+指标覆盖6大业务域")
print("  2. 🔧 MQL自动生成 - 8种操作符支持")
print("  3. ⚡ MQL执行引擎 - 高效查询模拟数据")
print("  4. 🔍 根因分析 - 4种分析类型")
print("  5. 🧠 智谱AI集成 - GLM-4 Flash")
print("  6. 🎨 可视化管理 - 图谱+意图双重可视化")
print("\n📚 API端点:")
print("  POST /api/v2/query        - 智能问数主接口")
print("  POST /api/v2/analyze     - 根因分析")
print("  GET  /api/v2/metrics      - 查询指标列表")
print("  GET  /api/v2/statistics   - 系统统计")
print("\n🌐 访问地址:")
print("  - API服务: http://localhost:8000")
print("  - API文档: http://localhost:8000/docs")
print("  - 图谱管理: frontend/graph-management.html")
print("")

EOF
