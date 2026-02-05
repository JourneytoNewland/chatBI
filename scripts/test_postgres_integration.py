"""PostgreSQL集成验证测试脚本.

测试完整的智能问数链路：
1. PostgreSQL连接测试
2. 基础查询测试
3. 聚合查询测试
4. 分组查询测试
5. 过滤查询测试
6. 性能测试
7. 智能解读测试
"""

import logging
import statistics
import time
from datetime import datetime, timedelta

from src.database.postgres_client import PostgreSQLClient
from src.inference.enhanced_hybrid import EnhancedHybridIntentRecognizer
from src.mql.generator import MQLGenerator
from src.mql.engine import MQLExecutionEngine
from src.mql.intelligent_interpreter import IntelligentInterpreter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntegrationTester:
    """集成测试器."""

    def __init__(self):
        """初始化."""
        self.postgres = PostgreSQLClient()
        self.intent_recognizer = EnhancedHybridIntentRecognizer(llm_provider="zhipu")
        self.mql_generator = MQLGenerator()
        self.mql_engine = MQLExecutionEngine()
        self.interpreter = IntelligentInterpreter()

    def run_all_tests(self):
        """运行所有测试."""
        print("\n🧪 PostgreSQL集成验证测试")
        print("=" * 60)

        tests = [
            ("PostgreSQL连接测试", self.test_connection),
            ("健康检查测试", self.test_health_check),
            ("基础查询测试", self.test_basic_query),
            ("聚合查询测试", self.test_aggregate_query),
            ("分组查询测试", self.test_group_by_query),
            ("过滤查询测试", self.test_filter_query),
            ("性能测试", self.test_performance),
            ("智能解读测试", self.test_intelligent_interpretation),
        ]

        passed = 0
        failed = 0

        for name, test_func in tests:
            print(f"\n📋 {name}")
            print("-" * 60)
            try:
                test_func()
                print(f"✅ 通过")
                passed += 1
            except Exception as e:
                print(f"❌ 失败: {e}")
                failed += 1

        print("\n" + "=" * 60)
        print(f"测试结果: {passed}通过, {failed}失败")
        print("=" * 60 + "\n")

        return failed == 0

    def test_connection(self):
        """测试PostgreSQL连接."""
        result = self.postgres.execute_query("SELECT 1 AS test")
        assert len(result) == 1
        assert result[0]["test"] == 1
        print("   连接成功")

    def test_health_check(self):
        """测试健康检查."""
        assert self.postgres.health_check()
        print("   健康检查通过")

    def test_basic_query(self):
        """测试基础查询: 最近7天的GMV."""
        from src.mql.mql import MQLQuery, TimeRange

        end = datetime.now()
        start = end - timedelta(days=7)

        mql_query = MQLQuery(
            metric="GMV",
            time_range=TimeRange(start=start, end=end, granularity="day")
        )

        result = self.mql_engine.execute(mql_query)

        print(f"   返回行数: {result['row_count']}")
        print(f"   执行时间: {result['execution_time_ms']}ms")
        print(f"   SQL: {result['sql'][:100]}...")

        assert result["row_count"] > 0, "应该返回数据"
        assert result["execution_time_ms"] < 1000, "执行时间应<1秒"

    def test_aggregate_query(self):
        """测试聚合查询: GMV总和."""
        from src.mql.mql import MQLQuery, TimeRange, MetricOperator

        end = datetime.now()
        start = end - timedelta(days=7)

        mql_query = MQLQuery(
            metric="GMV",
            operator=MetricOperator.SUM,
            time_range=TimeRange(start=start, end=end, granularity="day")
        )

        result = self.mql_engine.execute(mql_query)

        print(f"   返回行数: {result['row_count']}")
        print(f"   聚合结果: {result['result']}")
        print(f"   执行时间: {result['execution_time_ms']}ms")

        assert result["row_count"] <= 1, "聚合查询应返回单条记录"
        assert result["execution_time_ms"] < 1000, "执行时间应<1秒"

    def test_group_by_query(self):
        """测试分组查询: 按地区统计GMV."""
        from src.mql.mql import MQLQuery, TimeRange, MetricOperator, GroupBy

        end = datetime.now()
        start = end - timedelta(days=7)

        mql_query = MQLQuery(
            metric="GMV",
            operator=MetricOperator.SUM,
            time_range=TimeRange(start=start, end=end, granularity="day"),
            group_by=GroupBy(dimensions=["地区"])
        )

        result = self.mql_engine.execute(mql_query)

        print(f"   返回行数: {result['row_count']}")
        print(f"   分组结果示例: {result['result'][:3]}")
        print(f"   执行时间: {result['execution_time_ms']}ms")

        assert result["row_count"] > 0, "应返回分组数据"
        assert result["execution_time_ms"] < 1500, "执行时间应<1.5秒"

    def test_filter_query(self):
        """测试过滤查询: 华东地区GMV."""
        from src.mql.mql import MQLQuery, TimeRange, Filter

        end = datetime.now()
        start = end - timedelta(days=7)

        mql_query = MQLQuery(
            metric="GMV",
            time_range=TimeRange(start=start, end=end, granularity="day"),
            filters=[Filter(field="地区", operator="=", value="华东")]
        )

        result = self.mql_engine.execute(mql_query)

        print(f"   返回行数: {result['row_count']}")
        print(f"   过滤后结果示例: {result['result'][:2]}")
        print(f"   执行时间: {result['execution_time_ms']}ms")

        assert result["execution_time_ms"] < 1000, "执行时间应<1秒"

    def test_performance(self):
        """测试性能: 100次查询平均响应时间."""
        print("   正在执行100次查询...")

        from src.mql.mql import MQLQuery, TimeRange

        end = datetime.now()
        start = end - timedelta(days=7)

        execution_times = []

        for i in range(100):
            mql_query = MQLQuery(
                metric="GMV",
                time_range=TimeRange(start=start, end=end, granularity="day")
            )

            start_time = time.time()
            result = self.mql_engine.execute(mql_query)
            elapsed_ms = (time.time() - start_time) * 1000

            execution_times.append(elapsed_ms)

            if (i + 1) % 20 == 0:
                print(f"   进度: {i+1}/100")

        avg_time = statistics.mean(execution_times)
        median_time = statistics.median(execution_times)
        max_time = max(execution_times)
        min_time = min(execution_times)

        print(f"\n   性能统计:")
        print(f"   平均响应时间: {avg_time:.2f}ms")
        print(f"   中位数响应时间: {median_time:.2f}ms")
        print(f"   最大响应时间: {max_time:.2f}ms")
        print(f"   最小响应时间: {min_time:.2f}ms")

        assert avg_time < 500, f"平均响应时间应<500ms，实际{avg_time:.2f}ms"

    def test_intelligent_interpretation(self):
        """测试智能解读功能."""
        from src.mql.mql import MQLQuery, TimeRange

        end = datetime.now()
        start = end - timedelta(days=7)

        # 执行查询
        mql_query = MQLQuery(
            metric="GMV",
            time_range=TimeRange(start=start, end=end, granularity="day")
        )

        execution_result = self.mql_engine.execute(mql_query)

        # 生成智能解读
        metric_def = execution_result.get("metric", {})
        interpretation = self.interpreter.interpret(
            query="最近7天GMV",
            mql_result=execution_result,
            metric_def=metric_def
        )

        print(f"   总结: {interpretation.summary}")
        print(f"   趋势: {interpretation.trend}")
        print(f"   置信度: {interpretation.confidence:.2f}")
        print(f"   关键发现数量: {len(interpretation.key_findings)}")
        print(f"   深入洞察数量: {len(interpretation.insights)}")
        print(f"   行动建议数量: {len(interpretation.suggestions)}")

        assert interpretation.summary is not None, "总结不应为空"
        assert interpretation.trend in ["upward", "downward", "fluctuating", "stable"], "趋势值无效"
        assert 0 <= interpretation.confidence <= 1, "置信度应在0-1之间"
        assert len(interpretation.key_findings) > 0, "应有关键发现"
        assert len(interpretation.insights) > 0, "应有深入洞察"
        assert len(interpretation.suggestions) > 0, "应有行动建议"


def main():
    """主函数."""
    tester = IntegrationTester()

    try:
        success = tester.run_all_tests()
        exit(0 if success else 1)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}\n")
        raise

    finally:
        tester.postgres.close()


if __name__ == "__main__":
    main()
