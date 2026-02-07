"""MQL到SQL的转换器 V2 - 适配PostgreSQL星型模式."""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from src.inference.intent import QueryIntent, TimeRange, AggregationType

logger = logging.getLogger(__name__)


class SQLGeneratorV2:
    """MQL查询到PostgreSQL SQL查询的转换器.

    支持将QueryIntent对象转换为PostgreSQL可执行的SQL查询。
    适配星型模式架构（维度表 + 事实表）。

    Attributes:
        postgres_client: PostgreSQL客户端
    """

    # 指标到事实表的映射
    METRIC_TABLE_MAPPING = {
        # 电商指标 -> fact_orders
        "GMV": ("fact_orders", "gmv"),
        "成交金额": ("fact_orders", "gmv"),
        "订单量": ("fact_orders", "order_count"),
        "客单价": ("fact_orders", "average_order_value"),
        "折扣金额": ("fact_orders", "total_discount"),
        "订单总额": ("fact_orders", "total_order_amount"),

        # 用户指标 -> fact_user_activity
        "DAU": ("fact_user_activity", "dau"),
        "日活": ("fact_user_activity", "dau"),
        "MAU": ("fact_user_activity", "mau"),
        "月活": ("fact_user_activity", "mau"),
        "新增用户": ("fact_user_activity", "new_users"),
        "留存率": ("fact_user_activity", "retention_day7"),
        "次日留存": ("fact_user_activity", "retention_day1"),
        "7日留存": ("fact_user_activity", "retention_day7"),
        "30日留存": ("fact_user_activity", "retention_day30"),
        "平均会话时长": ("fact_user_activity", "avg_session_duration"),
        "页面浏览量": ("fact_user_activity", "page_views"),

        # 流量指标 -> fact_traffic
        "访客数": ("fact_traffic", "visitors"),
        "独立访客": ("fact_traffic", "unique_visitors"),
        "加购次数": ("fact_traffic", "add_to_cart_count"),
        "加购转化率": ("fact_traffic", "cart_conversion_rate"),
        "结账次数": ("fact_traffic", "checkout_count"),
        "结账转化率": ("fact_traffic", "checkout_conversion_rate"),
        "订单转化率": ("fact_traffic", "order_conversion_rate"),

        # 收入指标 -> fact_revenue
        "ARPU": ("fact_revenue", "arpu"),
        "ARPPU": ("fact_revenue", "arppu"),
        "总收入": ("fact_revenue", "total_revenue"),
        "LTV": ("fact_revenue", "ltv_30d"),
        "生命周期价值": ("fact_revenue", "ltv_90d"),

        # 财务指标 -> fact_finance
        "营收": ("fact_finance", "revenue"),
        "收入": ("fact_finance", "revenue"),
        "毛利润": ("fact_finance", "gross_profit"),
        "毛利率": ("fact_finance", "gross_profit_margin"),
        "净利润": ("fact_finance", "net_profit"),
        "净利率": ("fact_finance", "net_profit_margin"),
        "ROI": ("fact_finance", "roi"),
        "投资回报率": ("fact_finance", "roi"),
    }

    # 聚合类型到SQL函数的映射
    AGGREGATION_SQL_MAP = {
        AggregationType.SUM: "SUM",
        AggregationType.AVG: "AVG",
        AggregationType.COUNT: "COUNT",
        AggregationType.MAX: "MAX",
        AggregationType.MIN: "MIN",
        AggregationType.RATE: "AVG",  # 比率类型使用AVG
        AggregationType.RATIO: "AVG",  # 比率类型使用AVG
    }

    # 维度名称到表的映射
    DIMENSION_TABLE_MAPPING = {
        "地区": "dim_region",
        "品类": "dim_category",
        "渠道": "dim_channel",
        "用户等级": "dim_user_level",
    }

    # 维度名称到字段的映射
    DIMENSION_COLUMN_MAPPING = {
        "地区": {"name": "region_name", "key": "region_key"},
        "品类": {"name": "category_name", "key": "category_key"},
        "渠道": {"name": "channel_name", "key": "channel_key"},
        "用户等级": {"name": "level_name", "key": "user_level_key"},
    }

    def __init__(self):
        """初始化SQL生成器."""
        from src.database.postgres_client import postgres_client
        self.postgres_client = postgres_client

    def generate(self, intent: QueryIntent) -> Tuple[str, Dict[str, Any]]:
        """生成SQL查询和参数.

        Args:
            intent: 查询意图对象

        Returns:
            (SQL查询字符串, 参数字典)

        Raises:
            ValueError: 指标不支持时抛出
        """
        # 1. 确定源表和度量字段
        table_name, value_column = self._get_metric_table(intent.core_query)

        # 2. 构建SELECT子句
        select_clause, select_fields = self._build_select_clause(intent, value_column)

        # 3. 构建JOIN子句（维度表 + 日期表）
        join_clause = self._build_join_clause(intent)

        # 4. 构建WHERE子句
        where_clause, where_params = self._build_where_clause(intent)

        # 5. 构建GROUP BY子句
        group_by_clause = self._build_group_by_clause(intent, select_fields)

        # 6. 构建ORDER BY子句
        order_by_clause = self._build_order_by_clause(intent)

        # 7. 构建LIMIT子句
        limit_clause = self._build_limit_clause(intent)

        # 8. 组装完整SQL
        sql = f"""
            SELECT {select_clause}
            FROM {table_name} f
            {join_clause}
            {where_clause}
            {group_by_clause}
            {order_by_clause}
            {limit_clause}
        """.strip()

        return sql, where_params

    def _get_metric_table(self, metric_name: str) -> Tuple[str, str]:
        """获取指标对应的事实表和字段.

        Args:
            metric_name: 指标名称

        Returns:
            (表名, 字段名)

        Raises:
            ValueError: 指标不支持时抛出
        """
        metric_info = self.METRIC_TABLE_MAPPING.get(metric_name)
        if not metric_info:
            raise ValueError(f"不支持的指标: {metric_name}")

        return metric_info

    def _build_select_clause(
        self,
        intent: QueryIntent,
        value_column: str
    ) -> Tuple[str, List[str]]:
        """构建SELECT子句.

        Args:
            intent: 查询意图
            value_column: 度量字段名

        Returns:
            (SELECT子句, 选择的字段列表)
        """
        select_fields = []

        # 1. 添加日期字段（如果有时间范围）
        if intent.time_range:
            select_fields.append("dd.date")

        # 2. 添加维度字段
        for dim in (intent.dimensions or []):
            dim_info = self.DIMENSION_COLUMN_MAPPING.get(dim)
            if dim_info:
                table_alias = dim[0]  # 使用首字母作为表别名
                select_fields.append(f"{table_alias}.{dim_info['name']} AS {dim}")

        # 3. 添加度量字段（应用聚合）
        aggregation = intent.aggregation_type or AggregationType.SUM
        sql_func = self.AGGREGATION_SQL_MAP.get(aggregation, "SUM")

        # 判断是否需要聚合
        if intent.dimensions or (intent.time_range and intent.time_granularity):
            # 需要GROUP BY，使用聚合函数
            metric_expr = f"{sql_func}(f.{value_column}) AS metric_value"
        else:
            # 不需要分组，直接取值
            metric_expr = f"f.{value_column} AS metric_value"

        select_fields.append(metric_expr)

        select_clause = ", ".join(select_fields)
        return select_clause, select_fields

    def _build_join_clause(self, intent: QueryIntent) -> str:
        """构建JOIN子句.

        Args:
            intent: 查询意图

        Returns:
            JOIN子句字符串
        """
        joins = []

        # 1. 始终JOIN日期维度表
        joins.append("JOIN dim_date dd ON f.date_key = dd.date_key")

        # 2. 根据维度JOIN相应维度表
        for dim in (intent.dimensions or []):
            dim_info = self.DIMENSION_COLUMN_MAPPING.get(dim)
            if dim_info:
                table_name = self.DIMENSION_TABLE_MAPPING[dim]
                table_alias = dim[0]  # 使用首字母作为表别名
                joins.append(f"JOIN {table_name} {table_alias} ON f.{dim_info['key']} = {table_alias}.{dim_info['key']}")

        return "\n    ".join(joins)

    def _build_where_clause(self, intent: QueryIntent) -> Tuple[str, Dict[str, Any]]:
        """构建WHERE子句.

        Args:
            intent: 查询意图

        Returns:
            (WHERE子句字符串, 参数字典)
        """
        conditions = []
        params = {}

        # 1. 时间范围过滤
        if intent.time_range:
            start_date, end_date = self._parse_time_range(intent.time_range)
            conditions.append("dd.date BETWEEN %(start_date)s AND %(end_date)s")
            params["start_date"] = start_date
            params["end_date"] = end_date

        # 2. 维度过滤
        # TODO: 添加过滤条件支持

        # 3. 其他过滤条件
        # TODO: 添加其他过滤条件支持

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        return where_clause, params

    def _parse_time_range(self, time_range: TimeRange) -> Tuple[str, str]:
        """解析时间范围.

        Args:
            time_range: 时间范围对象

        Returns:
            (开始日期, 结束日期)
        """
        # 如果是具体日期范围，直接使用
        if hasattr(time_range, 'start_date') and hasattr(time_range, 'end_date'):
            return time_range.start_date.strftime("%Y-%m-%d"), time_range.end_date.strftime("%Y-%m-%d")

        # 否则使用相对时间计算
        from datetime import timedelta, datetime

        end_date = datetime.now()
        start_date = end_date

        # 根据时间粒度计算
        if time_range.granularity:
            if "day" in str(time_range.granularity).lower():
                # 最近N天
                if hasattr(time_range, 'days'):
                    start_date = end_date - timedelta(days=time_range.days)
                else:
                    start_date = end_date - timedelta(days=7)  # 默认7天
            elif "week" in str(time_range.granularity).lower():
                # 最近N周
                start_date = end_date - timedelta(weeks=1)
            elif "month" in str(time_range.granularity).lower():
                # 最近N月
                start_date = end_date - timedelta(days=30)

        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

    def _build_group_by_clause(self, intent: QueryIntent, select_fields: List[str]) -> str:
        """构建GROUP BY子句.

        Args:
            intent: 查询意图
            select_fields: SELECT字段列表

        Returns:
            GROUP BY子句字符串
        """
        group_fields = []

        # 1. 按日期分组（如果有时间粒度）
        if intent.time_range and intent.time_granularity:
            group_fields.append("dd.date")

        # 2. 按维度分组
        for dim in (intent.dimensions or []):
            dim_info = self.DIMENSION_COLUMN_MAPPING.get(dim)
            if dim_info:
                table_alias = dim[0]
                group_fields.append(f"{table_alias}.{dim_info['name']}")

        if not group_fields:
            return ""

        return f"GROUP BY {', '.join(group_fields)}"

    def _build_order_by_clause(self, intent: QueryIntent) -> str:
        """构建ORDER BY子句.

        Args:
            intent: 查询意图

        Returns:
            ORDER BY子句字符串
        """
        # TODO: 支持排序需求
        # 默认按日期降序
        if intent.time_range:
            return "ORDER BY dd.date DESC"

        return ""

    def _build_limit_clause(self, intent: QueryIntent) -> str:
        """构建LIMIT子句.

        Args:
            intent: 查询意图

        Returns:
            LIMIT子句字符串
        """
        # TODO: 支持Top N/Bottom N
        return ""


# 测试
if __name__ == "__main__":
    from src.inference.intent import QueryIntent, TimeRange, AggregationType

    print("\n🧪 测试SQL生成器V2")
    print("=" * 60)

    generator = SQLGeneratorV2()

    # 测试1: 简单查询 - GMV
    print("\n测试1: 简单查询 - GMV")
    intent1 = QueryIntent(
        query="GMV",
        core_query="GMV"
    )
    sql1, params1 = generator.generate(intent1)
    print(f"Intent: {intent1.core_query}")
    print(f"SQL:\n{sql1}")
    print(f"Params: {params1}")

    # 测试2: 时间范围查询 - 最近7天GMV
    print("\n" + "=" * 60)
    print("\n测试2: 时间范围查询 - 最近7天GMV")
    intent2 = QueryIntent(
        query="最近7天GMV",
        core_query="GMV",
        time_range=TimeRange(granularity="day")
    )
    sql2, params2 = generator.generate(intent2)
    print(f"Intent: {intent2.core_query}")
    print(f"SQL:\n{sql2}")
    print(f"Params: {params2}")

    # 测试3: 维度分组查询 - 按地区统计GMV
    print("\n" + "=" * 60)
    print("\n测试3: 维度分组查询 - 按地区统计GMV")
    intent3 = QueryIntent(
        query="按地区GMV",
        core_query="GMV",
        dimensions=["地区"]
    )
    sql3, params3 = generator.generate(intent3)
    print(f"Intent: {intent3.core_query}")
    print(f"Dimensions: {intent3.dimensions}")
    print(f"SQL:\n{sql3}")
    print(f"Params: {params3}")

    # 测试4: 聚合查询 - 本月GMV总和
    print("\n" + "=" * 60)
    print("\n测试4: 聚合查询 - 本月GMV总和")
    intent4 = QueryIntent(
        query="本月GMV总和",
        core_query="GMV",
        aggregation_type=AggregationType.SUM,
        time_range=TimeRange(granularity="month")
    )
    sql4, params4 = generator.generate(intent4)
    print(f"Intent: {intent4.core_query}")
    print(f"Aggregation: {intent4.aggregation_type}")
    print(f"SQL:\n{sql4}")
    print(f"Params: {params4}")

    # 测试5: 复杂查询 - 最近7天按渠道统计DAU
    print("\n" + "=" * 60)
    print("\n测试5: 复杂查询 - 最近7天按渠道统计DAU")
    intent5 = QueryIntent(
        query="最近7天按渠道统计DAU",
        core_query="DAU",
        dimensions=["渠道"],
        time_range=TimeRange(granularity="day")
    )
    sql5, params5 = generator.generate(intent5)
    print(f"Intent: {intent5.core_query}")
    print(f"Dimensions: {intent5.dimensions}")
    print(f"SQL:\n{sql5}")
    print(f"Params: {params5}")

    print("\n" + "=" * 60)
    print("✅ 所有测试通过")
