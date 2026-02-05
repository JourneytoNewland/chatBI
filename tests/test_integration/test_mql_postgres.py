"""MQL与PostgreSQL集成测试."""

import pytest
from datetime import datetime
from src.mql.engine import MQLExecutionEngine
from src.mql.generator import MQLGenerator
from src.mql.mql import MQLQuery, MetricOperator, TimeRange


@pytest.mark.integration
class TestMQLPostgresIntegration:
    """MQL执行引擎与PostgreSQL集成测试."""

    def test_engine_initialization(self):
        """测试引擎初始化."""
        engine = MQLExecutionEngine()
        assert engine.postgres is not None
        assert engine.sql_generator is not None
        assert engine.registry is not None

    def test_simple_query_execution(self):
        """测试简单查询执行: 最近7天的GMV."""
        engine = MQLExecutionEngine()

        # 创建MQL查询
        mql_query = MQLQuery(
            metric="GMV",
            time_range=TimeRange(
                start=datetime(2024, 1, 1),
                end=datetime(2024, 1, 7),
                granularity="day"
            )
        )

        # 执行查询
        result = engine.execute(mql_query)

        # 验证结果
        assert "query" in result
        assert "metric" in result
        assert "sql" in result
        assert "result" in result
        assert "row_count" in result
        assert "execution_time_ms" in result

        # SQL应该被生成
        assert result["sql"] is not None
        assert "SELECT" in result["sql"].upper()

    def test_aggregate_query(self):
        """测试聚合查询: GMV总和."""
        engine = MQLExecutionEngine()

        mql_query = MQLQuery(
            metric="GMV",
            operator=MetricOperator.SUM,
            time_range=TimeRange(
                start=datetime(2024, 1, 1),
                end=datetime(2024, 1, 7),
                granularity="day"
            )
        )

        result = engine.execute(mql_query)

        # 应该包含聚合操作
        assert "SUM" in result["sql"]
        # 聚合查询应该返回单条记录
        assert len(result["result"]) <= 1

    def test_degradation_mechanism(self):
        """测试降级机制: PostgreSQL失败时使用模拟数据."""
        # 这个测试需要模拟PostgreSQL失败的场景
        # 当前先跳过，需要在生产环境中测试
        pytest.skip("需要模拟PostgreSQL故障场景")

    def test_end_to_end_query(self):
        """测试端到端查询流程."""
        engine = MQLExecutionEngine()

        # 测试查询: "最近7天GMV总和"
        mql_query = MQLQuery(
            metric="GMV",
            operator=MetricOperator.SUM,
            time_range=TimeRange(
                start=datetime.now(),
                end=datetime.now(),
                granularity="day"
            )
        )

        result = engine.execute(mql_query)

        # 验证响应格式
        assert isinstance(result, dict)
        assert "sql" in result
        assert "execution_time_ms" in result

        # 如果PostgreSQL连接正常，应该返回真实数据
        # 如果连接失败，应该降级到模拟数据
        print(f"\n生成的SQL: {result['sql']}")
        print(f"执行时间: {result['execution_time_ms']}ms")
        print(f"返回行数: {result['row_count']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
