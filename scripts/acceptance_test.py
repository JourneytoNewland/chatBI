"""项目验收测试脚本.

测试完整的功能（不需要PostgreSQL运行）：
1. 模块导入测试
2. SQL生成器测试
3. 智能解读器测试（含模拟数据）
4. 降级机制测试
"""

import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_module_imports():
    """测试1: 模块导入."""
    print("\n" + "=" * 60)
    print("📦 测试1: 模块导入")
    print("=" * 60)

    try:
        from src.database.postgres_client import PostgreSQLClient
        print("✅ PostgreSQL客户端")

        from src.mql.sql_generator import SQLGenerator
        print("✅ SQL生成器")

        from src.mql.intelligent_interpreter import IntelligentInterpreter
        print("✅ 智能解读器")

        from src.mql.models import InterpretationResult
        print("✅ MQL数据模型")

        from src.api.v2_query_api import create_app
        print("✅ API服务")

        print("\n✅ 所有核心模块导入成功")
        return True

    except Exception as e:
        print(f"\n❌ 模块导入失败: {e}")
        return False


def test_sql_generator():
    """测试2: SQL生成器."""
    print("\n" + "=" * 60)
    print("🔧 测试2: SQL生成器")
    print("=" * 60)

    try:
        from src.mql.sql_generator import SQLGenerator
        from src.mql.mql import MQLQuery, MetricOperator, TimeRange

        generator = SQLGenerator()

        # 测试聚合查询
        mql_query = MQLQuery(
            metric="GMV",
            operator=MetricOperator.SUM,
            time_range=TimeRange(
                start=datetime(2024, 1, 1),
                end=datetime(2024, 1, 7),
                granularity="day"
            )
        )

        sql, params = generator.generate(mql_query)

        print(f"\n生成的SQL:")
        print(f"  {sql[:100]}...")
        print(f"\n参数:")
        print(f"  {params}")

        # 验证SQL包含关键元素
        assert "SUM" in sql, "SQL应包含SUM聚合"
        assert "fact_orders" in sql, "SQL应引用订单事实表"
        assert "BETWEEN" in sql, "SQL应包含时间范围过滤"

        print("\n✅ SQL生成器测试通过")
        return True

    except Exception as e:
        print(f"\n❌ SQL生成器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_intelligent_interpreter():
    """测试3: 智能解读器."""
    print("\n" + "=" * 60)
    print("🤖 测试3: 智能解读器")
    print("=" * 60)

    try:
        from src.mql.intelligent_interpreter import IntelligentInterpreter

        interpreter = IntelligentInterpreter()

        # 生成上升趋势的模拟数据
        mock_data = []
        for i in range(7):
            mock_data.append({
                "date": (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d"),
                "value": 500000 + i * 30000,  # 上升趋势
                "metric": "GMV",
                "unit": "元"
            })

        metric_def = {
            "name": "GMV",
            "description": "商品交易总额",
            "unit": "元"
        }

        mql_result = {
            "result": mock_data,
            "row_count": len(mock_data)
        }

        # 执行解读
        interpretation = interpreter.interpret(
            query="最近7天GMV",
            mql_result=mql_result,
            metric_def=metric_def
        )

        print(f"\n解读结果:")
        print(f"  总结: {interpretation.summary}")
        print(f"  趋势: {interpretation.trend}")
        print(f"  置信度: {interpretation.confidence:.2f}")
        print(f"\n  关键发现:")
        for finding in interpretation.key_findings[:2]:
            print(f"    - {finding}")
        print(f"\n  深入洞察:")
        for insight in interpretation.insights[:2]:
            print(f"    - {insight}")
        print(f"\n  行动建议:")
        for suggestion in interpretation.suggestions[:2]:
            print(f"    - {suggestion}")

        # 验证解读结果
        assert interpretation.trend == "upward", "应识别为上升趋势"
        assert interpretation.summary is not None, "总结不应为空"
        assert len(interpretation.key_findings) > 0, "应有关键发现"
        assert len(interpretation.insights) > 0, "应有深入洞察"
        assert len(interpretation.suggestions) > 0, "应有行动建议"
        assert 0 <= interpretation.confidence <= 1, "置信度应在0-1之间"

        print("\n✅ 智能解读器测试通过")
        return True

    except Exception as e:
        print(f"\n❌ 智能解读器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fallback_mechanism():
    """测试4: 降级机制."""
    print("\n" + "=" * 60)
    print("🛡️ 测试4: 降级机制")
    print("=" * 60)

    try:
        from src.mql.intelligent_interpreter import IntelligentInterpreter

        interpreter = IntelligentInterpreter()

        # 生成模拟数据
        mock_data = []
        for i in range(7):
            mock_data.append({
                "date": (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d"),
                "value": 500000 + i * 20000,
                "metric": "GMV",
                "unit": "元"
            })

        metric_def = {
            "name": "GMV",
            "description": "商品交易总额",
            "unit": "元"
        }

        mql_result = {
            "result": mock_data,
            "row_count": len(mock_data)
        }

        # 使用模板解读（模拟LLM失败）
        interpretation = interpreter._generate_template_interpretation(
            query="最近7天GMV",
            data_analysis=interpreter._analyze_data(mock_data),
            metric_def=metric_def,
            mql_result=mql_result
        )

        print(f"\n模板解读结果:")
        print(f"  总结: {interpretation.summary}")
        print(f"  关键发现数量: {len(interpretation.key_findings)}")
        print(f"  深入洞察数量: {len(interpretation.insights)}")
        print(f"  行动建议数量: {len(interpretation.suggestions)}")

        # 验证模板解读
        assert interpretation.summary is not None, "总结不应为空"
        assert len(interpretation.key_findings) > 0, "应有关键发现"
        assert len(interpretation.insights) > 0, "应有深入洞察"
        assert len(interpretation.suggestions) > 0, "应有行动建议"

        print("\n✅ 降级机制测试通过")
        return True

    except Exception as e:
        print(f"\n❌ 降级机制测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_analysis():
    """测试5: 数据分析."""
    print("\n" + "=" * 60)
    print("📊 测试5: 数据分析")
    print("=" * 60)

    try:
        from src.mql.intelligent_interpreter import IntelligentInterpreter

        interpreter = IntelligentInterpreter()

        # 上升趋势数据
        upward_data = [{"value": 100 + i * 10} for i in range(10)]
        analysis = interpreter._analyze_data(upward_data)

        print(f"\n上升趋势分析:")
        print(f"  趋势: {analysis['trend']}")
        print(f"  变化率: {analysis['change_rate']:.2f}%")
        print(f"  波动性: {analysis['volatility']:.2f}%")

        assert analysis["trend"] == "upward", "应识别为上升趋势"
        assert analysis["change_rate"] > 0, "变化率应大于0"

        # 下降趋势数据
        downward_data = [{"value": 200 - i * 10} for i in range(10)]
        analysis = interpreter._analyze_data(downward_data)

        print(f"\n下降趋势分析:")
        print(f"  趋势: {analysis['trend']}")
        print(f"  变化率: {analysis['change_rate']:.2f}%")

        assert analysis["trend"] == "downward", "应识别为下降趋势"

        # 稳定数据
        stable_data = [{"value": 100 + (i % 2) * 2} for i in range(10)]
        analysis = interpreter._analyze_data(stable_data)

        print(f"\n稳定数据分析:")
        print(f"  趋势: {analysis['trend']}")
        print(f"  变化率: {analysis['change_rate']:.2f}%")

        assert analysis["trend"] == "stable", "应识别为稳定趋势"

        print("\n✅ 数据分析测试通过")
        return True

    except Exception as e:
        print(f"\n❌ 数据分析测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数."""
    print("\n🚀 项目验收测试")
    print("=" * 60)
    print("注意：此测试不需要PostgreSQL运行")
    print("=" * 60)

    tests = [
        ("模块导入", test_module_imports),
        ("SQL生成器", test_sql_generator),
        ("智能解读器", test_intelligent_interpreter),
        ("降级机制", test_fallback_mechanism),
        ("数据分析", test_data_analysis),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ {name}测试异常: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed}通过, {failed}失败")
    print("=" * 60)

    if failed == 0:
        print("\n🎉 所有验收测试通过！")
        print("\n下一步:")
        print("  1. 安装Docker Desktop (如未安装)")
        print("  2. 启动服务: docker compose up -d")
        print("  3. 初始化数据: python scripts/init_test_data.py")
        print("  4. 运行集成测试: python scripts/test_postgres_integration.py")
        print("  5. 启动API: python -m src.api.v2_query_api")
        print("\n详细文档: docs/POSTGRESQL_INTEGRATION.md")
        print("=" * 60 + "\n")
    else:
        print("\n❌ 部分测试失败，请检查错误信息")
        print("=" * 60 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
