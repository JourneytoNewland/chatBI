"""MQL生成器 - 从意图生成MQL查询."""

from datetime import datetime, timedelta
from typing import Optional

from .mql import MQLQuery, MetricOperator, ComparisonType, TimeRange, Filter, GroupBy
from ..inference.intent import QueryIntent, AggregationType


class MQLGenerator:
    """MQL生成器.

    将QueryIntent转换为MQLQuery。
    """

    def generate(self, intent: QueryIntent) -> MQLQuery:
        """从意图生成MQL查询.

        Args:
            intent: 查询意图对象

        Returns:
            MQL查询对象
        """
        # 1. 确定指标和操作符
        metric, operator = self._determine_metric_and_operator(intent)

        # 2. 转换时间范围
        time_range = self._convert_time_range(intent)

        # 3. 转换分组维度
        group_by = self._convert_group_by(intent)

        # 4. 转换过滤条件
        filters = self._convert_filters(intent)

        # 5. 转换比较类型
        comparison = self._convert_comparison(intent.comparison_type)

        # 6. 构建查询
        return MQLQuery(
            metric=metric,
            operator=operator,
            time_range=time_range,
            group_by=group_by,
            filters=filters,
            comparison=comparison,
            order_by=None,
            order_limit=10
        )

    def _determine_metric_and_operator(self, intent: QueryIntent) -> tuple[str, MetricOperator]:
        """确定指标和操作符."""
        # 核心查询词就是指标名
        metric = intent.core_query

        # 根据聚合类型确定操作符
        if intent.aggregation_type == AggregationType.SUM:
            operator = MetricOperator.SUM
        elif intent.aggregation_type == AggregationType.AVG:
            operator = MetricOperator.AVG
        elif intent.aggregation_type == AggregationType.COUNT:
            operator = MetricOperator.COUNT
        elif intent.aggregation_type == AggregationType.MAX:
            operator = MetricOperator.MAX
        elif intent.aggregation_type == AggregationType.MIN:
            operator = MetricOperator.MIN
        elif intent.aggregation_type == AggregationType.RATE:
            operator = MetricOperator.RATE
        elif intent.aggregation_type == AggregationType.RATIO:
            operator = MetricOperator.RATIO
        else:
            operator = MetricOperator.SELECT

        return metric, operator

    def _convert_time_range(self, intent: QueryIntent) -> Optional[TimeRange]:
        """转换时间范围."""
        if not intent.time_range:
            return None

        start, end = intent.time_range

        # 确定粒度
        granularity = "day"
        if intent.time_granularity:
            granularity = intent.time_granularity.value

        return TimeRange(
            start=start,
            end=end,
            granularity=granularity
        )

    def _convert_group_by(self, intent: QueryIntent) -> Optional[GroupBy]:
        """转换分组维度."""
        if not intent.dimensions:
            return None

        return GroupBy(dimensions=intent.dimensions)

    def _convert_filters(self, intent: QueryIntent) -> list:
        """转换过滤条件."""
        filters = []

        # 从意图的filters中提取
        for key, value in intent.filters.items():
            if key == "domain":
                filters.append(Filter(
                    field="domain",
                    operator="=",
                    value=value
                ))

        return filters

    def _convert_comparison(self, comparison_type: Optional[str]) -> Optional[ComparisonType]:
        """转换比较类型."""
        if not comparison_type:
            return None

        comparison_map = {
            "yoy": ComparisonType.YOY,
            "mom": ComparisonType.MOM,
            "wow": ComparisonType.WOW,
            "dod": ComparisonType.DOD
        }

        return comparison_map.get(comparison_type.lower())


# 测试函数
def test_mql_generator():
    """测试MQL生成器."""
    from ..inference.intent import IntentRecognizer, TimeGranularity, AggregationType

    print("\n🧪 测试MQL生成器")
    print("=" * 60)

    generator = MQLGenerator()
    recognizer = IntentRecognizer()

    test_cases = [
        ("GMV", "简单查询"),
        ("最近7天的GMV总和", "时间范围+聚合"),
        ("按地区的GMV", "分组查询"),
        ("GMV同比", "比较查询"),
        ("本月按地区的成交金额总和", "复杂查询"),
    ]

    for query, desc in test_cases:
        print(f"\n测试: {desc}")
        print(f"查询: {query}")
        print("-" * 60)

        # 识别意图
        intent = recognizer.recognize(query)

        # 生成MQL
        mql_query = generator.generate(intent)

        print(f"✅ 生成的MQL:")
        print(str(mql_query))
        print()


if __name__ == "__main__":
    test_mql_generator()
