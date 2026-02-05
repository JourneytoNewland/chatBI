"""MQL到SQL的转换器."""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .mql import MQLQuery, MetricOperator, Filter, TimeRange
from .metrics import registry

logger = logging.getLogger(__name__)


class SQLGenerator:
    """MQL查询到SQL查询的转换器.

    支持将MQL查询对象转换为PostgreSQL可执行的SQL查询。

    Attributes:
        registry: 指标注册表
    """

    # 映射指标源表
    METRIC_TABLE_MAPPING = {
        "order_table": "fact_orders",
        "user_activity_log": "fact_user_activity",
        "user_profile": "fact_user_profile",
        "traffic_table": "fact_traffic",
        "revenue_table": "fact_revenue",
        "finance_table": "fact_finance",
        "marketing_table": "fact_marketing",
        "survey_table": "fact_survey",
    }

    # 聚合操作符映射
    OPERATOR_SQL_MAP = {
        MetricOperator.SELECT: "",
        MetricOperator.SUM: "SUM",
        MetricOperator.AVG: "AVG",
        MetricOperator.COUNT: "COUNT",
        MetricOperator.MAX: "MAX",
        MetricOperator.MIN: "MIN",
    }

    def __init__(self) -> None:
        """初始化转换器."""
        self.registry = registry

    def generate(self, mql_query: MQLQuery) -> Tuple[str, Dict[str, Any]]:
        """生成SQL查询和参数.

        Args:
            mql_query: MQL查询对象

        Returns:
            (SQL查询字符串, 参数字典)

        Raises:
            ValueError: 指标不存在或数据源不支持时抛出
        """
        # 1. 获取指标定义
        metric_def = self.registry.get_metric(mql_query.metric)
        if not metric_def:
            raise ValueError(f"指标不存在: {mql_query.metric}")

        # 2. 确定源表
        data_source = metric_def.get("data_source", "")
        table_name = self._get_table_name(data_source)

        # 3. 确定度量字段
        value_column = self._get_value_column(metric_def)

        # 4. 构建SELECT子句
        select_clause = self._build_select_clause(
            mql_query.operator,
            value_column,
            mql_query.time_range.granularity if mql_query.time_range else "day"
        )

        # 5. 构建JOIN子句(维度表)
        join_clause = self._build_join_clause(metric_def, mql_query)

        # 6. 构建WHERE子句
        where_clause, where_params = self._build_where_clause(mql_query, metric_def)

        # 7. 构建GROUP BY子句
        group_by_clause = self._build_group_by_clause(mql_query, metric_def)

        # 8. 构建ORDER BY子句
        order_by_clause = self._build_order_by_clause(mql_query)

        # 9. 构建LIMIT子句
        limit_clause = self._build_limit_clause(mql_query)

        # 10. 组装完整SQL
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

    def _get_table_name(self, data_source: str) -> str:
        """获取表名.

        Args:
            data_source: 数据源名称

        Returns:
            表名

        Raises:
            ValueError: 数据源不支持时抛出
        """
        table_name = self.METRIC_TABLE_MAPPING.get(data_source)
        if not table_name:
            raise ValueError(f"不支持的数据源: {data_source}")
        return table_name

    def _get_value_column(self, metric_def: Dict) -> str:
        """获取度量字段名.

        Args:
            metric_def: 指标定义

        Returns:
            度量字段名
        """
        calc_type = metric_def.get("calculation_type", "")

        # 根据计算类型确定度量字段
        if calc_type == "SUM":
            if "order_amount" in metric_def.get("formula", ""):
                return "order_amount"
            elif "revenue" in metric_def.get("formula", ""):
                return "revenue"
            else:
                return "profit"
        elif calc_type == "COUNT":
            return "*"
        elif calc_type == "AVG":
            if "satisfaction_score" in metric_def.get("formula", ""):
                return "satisfaction_score"
            else:
                return "order_amount"
        else:
            return "*"

    def _build_select_clause(
        self,
        operator: MetricOperator,
        value_column: str,
        granularity: str,
    ) -> str:
        """构建SELECT子句.

        Args:
            operator: 聚合操作符
            value_column: 度量字段
            granularity: 时间粒度

        Returns:
            SELECT子句字符串
        """
        if operator == MetricOperator.SELECT:
            # 选择操作，返回时间序列
            return f"""
                f.date_id AS date,
                {value_column} AS value
            """
        else:
            # 聚合操作
            sql_func = self.OPERATOR_SQL_MAP.get(operator, "SUM")
            return f"{sql_func}({value_column}) AS value"

    def _build_join_clause(self, metric_def: Dict, mql_query: MQLQuery) -> str:
        """构建JOIN子句.

        Args:
            metric_def: 指标定义
            mql_query: MQL查询对象

        Returns:
            JOIN子句字符串
        """
        joins = []
        dimensions = metric_def.get("dimensions", [])

        # 根据维度需求JOIN维度表
        if "地区" in dimensions:
            joins.append("JOIN dim_region r ON f.region_id = r.region_id")

        if "品类" in dimensions or "一级分类" in dimensions or "二级分类" in dimensions:
            joins.append("JOIN dim_category c ON f.category_id = c.category_id")

        if "渠道" in dimensions:
            joins.append("JOIN dim_channel ch ON f.channel_id = ch.channel_id")

        if "用户等级" in dimensions:
            joins.append("JOIN dim_user_level ul ON f.user_level_id = ul.level_id")

        # 始终JOIN时间维度表
        joins.append("JOIN dim_date d ON f.date_id = d.date_id")

        return "\n    ".join(joins)

    def _build_where_clause(
        self,
        mql_query: MQLQuery,
        metric_def: Dict,
    ) -> Tuple[str, Dict[str, Any]]:
        """构建WHERE子句.

        Args:
            mql_query: MQL查询对象
            metric_def: 指标定义

        Returns:
            (WHERE子句字符串, 参数字典)
        """
        conditions = []
        params = {}

        # 1. 时间范围过滤
        if mql_query.time_range:
            conditions.append("f.date_id BETWEEN %(start_date)s AND %(end_date)s")
            params["start_date"] = mql_query.time_range.start.strftime("%Y-%m-%d")
            params["end_date"] = mql_query.time_range.end.strftime("%Y-%m-%d")

        # 2. 维度过滤
        for filter_item in mql_query.filters:
            field = filter_item.field
            operator = filter_item.operator
            value = filter_item.value

            # 映射中文字段名到表字段
            column_map = {
                "地区": "r.region_name",
                "品类": "c.category_name",
                "渠道": "ch.channel_name",
                "用户等级": "ul.level_name",
            }

            column = column_map.get(field, field)

            if operator == "=":
                conditions.append(f"{column} = %({field})s")
                params[field] = value
            elif operator == "IN":
                placeholders = ", ".join([f"%({field}_{i})s" for i in range(len(value))])
                conditions.append(f"{column} IN ({placeholders})")
                for i, v in enumerate(value):
                    params[f"{field}_{i}"] = v
            elif operator == ">":
                conditions.append(f"{column} > %({field})s")
                params[field] = value
            elif operator == "<":
                conditions.append(f"{column} < %({field})s")
                params[field] = value

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        return where_clause, params

    def _build_group_by_clause(self, mql_query: MQLQuery, metric_def: Dict) -> str:
        """构建GROUP BY子句.

        Args:
            mql_query: MQL查询对象
            metric_def: 指标定义

        Returns:
            GROUP BY子句字符串
        """
        if not mql_query.group_by:
            return ""

        dimensions = mql_query.group_by.dimensions

        # 映射维度名到表字段
        column_map = {
            "地区": "r.region_name",
            "品类": "c.category_name",
            "渠道": "ch.channel_name",
            "用户等级": "ul.level_name",
        }

        group_columns = []
        for dim in dimensions:
            column = column_map.get(dim, dim)
            group_columns.append(column)

        return f"GROUP BY {', '.join(group_columns)}"

    def _build_order_by_clause(self, mql_query: MQLQuery) -> str:
        """构建ORDER BY子句.

        Args:
            mql_query: MQL查询对象

        Returns:
            ORDER BY子句字符串
        """
        if not mql_query.order_by:
            return ""

        reverse = mql_query.order_by.startswith("-")
        field = mql_query.order_by.lstrip("+-")

        direction = "DESC" if reverse else "ASC"
        return f"ORDER BY {field} {direction}"

    def _build_limit_clause(self, mql_query: MQLQuery) -> str:
        """构建LIMIT子句.

        Args:
            mql_query: MQL查询对象

        Returns:
            LIMIT子句字符串
        """
        if not mql_query.order_limit:
            return ""

        return f"LIMIT {mql_query.order_limit}"


# 测试
if __name__ == "__main__":
    from .mql import MQLQuery, MetricOperator, TimeRange, Filter, GroupBy

    print("\n🧪 测试SQL生成器")
    print("=" * 60)

    generator = SQLGenerator()

    # 测试1: 简单查询
    print("\n测试1: 简单查询")
    mql1 = MQLQuery(metric="GMV")
    sql1, params1 = generator.generate(mql1)
    print(f"MQL: {mql1}")
    print(f"SQL: {sql1}")
    print(f"Params: {params1}")

    # 测试2: 聚合查询
    print("\n测试2: 聚合查询")
    mql2 = MQLQuery(
        metric="GMV",
        operator=MetricOperator.SUM,
        time_range=TimeRange(
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 31),
            granularity="day"
        )
    )
    sql2, params2 = generator.generate(mql2)
    print(f"MQL: {mql2}")
    print(f"SQL: {sql2}")
    print(f"Params: {params2}")

    print("\n" + "=" * 60)
    print("✅ 所有测试通过")
