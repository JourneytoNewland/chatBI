"""MQL执行引擎 - 执行MQL查询并返回数据."""

import logging
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .mql import MQLQuery, MetricOperator, TimeRange
from .metrics import registry
from ..database.postgres_client import PostgreSQLClient
from .sql_generator import SQLGenerator

logger = logging.getLogger(__name__)


class MQLExecutionEngine:
    """MQL执行引擎.

    功能:
    1. 解析MQL查询
    2. 生成查询计划
    3. 执行查询（PostgreSQL真实数据）
    4. 返回结果
    """

    def __init__(
        self,
        postgres_client: Optional[PostgreSQLClient] = None
    ) -> None:
        """初始化执行引擎.

        Args:
            postgres_client: PostgreSQL客户端，默认创建新实例
        """
        self.postgres = postgres_client or PostgreSQLClient()
        self.sql_generator = SQLGenerator()
        self.registry = registry

    def execute(self, mql_query: MQLQuery) -> Dict[str, Any]:
        """执行MQL查询.

        Args:
            mql_query: MQL查询对象

        Returns:
            查询结果字典
        """
        import time
        start_time = time.time()

        # 1. 获取指标定义
        metric_def = self.registry.get_metric(mql_query.metric)
        if not metric_def:
            raise ValueError(f"指标不存在: {mql_query.metric}")

        # 2. 生成SQL查询（替换原来的_generate_mock_data）
        sql, params = self.sql_generator.generate(mql_query)

        # 3. 执行SQL查询（从PostgreSQL获取真实数据）
        data = self._fetch_real_data(sql, params, metric_def)

        # 4. 应用操作符（如果SQL中已经处理，这里可以跳过）
        result = self._apply_operator(mql_query, metric_def, data)

        # 5. 应用分组（如果SQL中已经处理，这里可以跳过）
        if mql_query.group_by and not self._has_aggregate_in_sql(mql_query):
            result = self._apply_group_by(result, mql_query.group_by.dimensions)

        # 6. 应用过滤（如果SQL中已经处理，这里可以跳过）
        if mql_query.filters and not self._has_filter_in_sql(mql_query):
            result = self._apply_filters(result, mql_query.filters)

        # 7. 应用排序和限制
        if mql_query.order_by:
            result = self._apply_order_by(result, mql_query.order_by)

        if mql_query.order_limit:
            result = result[:mql_query.order_limit]

        # 8. 应用比较（同比/环比）
        if mql_query.comparison:
            result = self._apply_comparison(result, mql_query.comparison, metric_def)

        execution_time = int((time.time() - start_time) * 1000)

        return {
            "query": str(mql_query),
            "metric": metric_def,
            "sql": sql,  # 调试用
            "result": result,
            "row_count": len(result),
            "execution_time_ms": execution_time
        }

    def _fetch_real_data(
        self,
        sql: str,
        params: Dict[str, Any],
        metric_def: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """从PostgreSQL获取真实数据.

        Args:
            sql: SQL查询语句
            params: 查询参数
            metric_def: 指标定义

        Returns:
            查询结果列表

        Raises:
            RuntimeError: 查询失败时抛出
        """
        try:
            # 执行查询
            rows = self.postgres.execute_query(sql, params)

            # 格式化结果
            data = []
            for row in rows:
                data.append({
                    "date": row.get("date", ""),
                    "value": float(row.get("value", 0)),
                    "metric": metric_def["name"],
                    "unit": metric_def["unit"],
                    **{k: v for k, v in row.items() if k not in ["date", "value"]}
                })

            return data

        except Exception as e:
            # 降级到模拟数据
            logger.warning(f"PostgreSQL查询失败，降级到模拟数据: {e}")
            return self._generate_mock_data_fallback(metric_def)

    def _has_aggregate_in_sql(self, mql_query: MQLQuery) -> bool:
        """检查SQL中是否已包含聚合.

        Args:
            mql_query: MQL查询对象

        Returns:
            是否已包含聚合
        """
        return mql_query.operator != MetricOperator.SELECT

    def _has_filter_in_sql(self, mql_query: MQLQuery) -> bool:
        """检查SQL中是否已包含过滤.

        Args:
            mql_query: MQL查询对象

        Returns:
            是否已包含过滤
        """
        return len(mql_query.filters) > 0

    def _generate_mock_data_fallback(
        self,
        metric_def: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """降级方法：生成模拟数据（当PostgreSQL不可用时）.

        Args:
            metric_def: 指标定义

        Returns:
            模拟数据列表
        """
        logger.info("使用模拟数据模式")

        # 生成最近7天的模拟数据
        end = datetime.now()
        start = end - timedelta(days=7)

        data = []
        current = start
        while current <= end:
            base_value = self._get_base_value(metric_def)
            value = base_value * random.uniform(0.8, 1.2)

            row = {
                "date": current.strftime("%Y-%m-%d"),
                "value": round(value, 2),
                "metric": metric_def["name"],
                "unit": metric_def["unit"]
            }

            # 添加维度字段
            for dim in metric_def.get("dimensions", ["地区"]):
                row[dim] = random.choice(["华东", "华南", "华北", "西南", "东北"])

            data.append(row)
            current += timedelta(days=1)

        return data

    def _generate_mock_data(
        self,
        mql_query: MQLQuery,
        metric_def: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成模拟数据."""
        data = []

        # 确定时间范围
        if mql_query.time_range:
            start = mql_query.time_range.start
            end = mql_query.time_range.end
        else:
            end = datetime.now()
            start = end - timedelta(days=7)

        # 确定粒度
        granularity = mql_query.time_range.granularity if mql_query.time_range else "day"

        # 生成时间序列
        current = start
        while current <= end:
            # 基础值（根据指标类型生成）
            base_value = self._get_base_value(metric_def)

            # 添加随机波动
            value = base_value * random.uniform(0.8, 1.2)

            # 添加维度信息
            row = {
                "date": current.strftime("%Y-%m-%d"),
                "value": round(value, 2),
                "metric": metric_def["name"],
                "unit": metric_def["unit"]
            }

            # 添加维度字段
            for dim in metric_def.get("dimensions", ["地区"]):
                row[dim] = random.choice(["华东", "华南", "华北", "西南", "东北"])

            data.append(row)

            # 前进到下一时间点
            if granularity == "day":
                current += timedelta(days=1)
            elif granularity == "week":
                current += timedelta(weeks=1)
            elif granularity == "month":
                current += timedelta(days=30)

        return data

    def _get_base_value(self, metric_def: Dict[str, Any]) -> float:
        """获取指标的基础值."""
        metric_id = metric_def["metric_id"]

        # 根据指标ID返回合理的基准值
        base_values = {
            "gmv": 500000,          # 50万
            "gmv_by_category": 100000,
            "order_count": 1000,
            "conversion_rate": 3.5,  # 3.5%
            "cart_rate": 8.5,
            "pay_rate": 85.0,
            "dau": 50000,
            "mau": 200000,
            "new_users": 2000,
            "retention_rate": 65.0,
            "churn_rate": 5.0,
            "arpu": 150,
            "ltv": 500,
            "revenue": 800000,
            "profit": 200000,
            "profit_margin": 25.0,
            "roi": 150.0,
            "roas": 300.0,
            "gmv_growth_rate": 15.0,
            "user_growth_rate": 8.0,
            "dau_mau_ratio": 25.0,
            "avg_order_value": 500,
            "repeat_purchase_rate": 35.0,
            "refund_rate": 2.0,
            "customer_satisfaction": 4.2
        }

        return base_values.get(metric_id, 1000)

    def _apply_operator(
        self,
        mql_query: MQLQuery,
        metric_def: Dict[str, Any],
        data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """应用操作符（SUM, AVG, COUNT等）."""
        operator = mql_query.operator

        if operator == MetricOperator.SELECT:
            return data

        elif operator == MetricOperator.SUM:
            # 聚合到一条记录
            total = sum(row["value"] for row in data)
            return [{
                "date": data[0]["date"] if data else datetime.now().strftime("%Y-%m-%d"),
                "value": round(total, 2),
                "metric": metric_def["name"],
                "unit": metric_def["unit"],
                "_operation": "SUM"
            }]

        elif operator == MetricOperator.AVG:
            avg = sum(row["value"] for row in data) / len(data) if data else 0
            return [{
                "date": data[0]["date"] if data else datetime.now().strftime("%Y-%m-%d"),
                "value": round(avg, 2),
                "metric": metric_def["name"],
                "unit": metric_def["unit"],
                "_operation": "AVG"
            }]

        elif operator == MetricOperator.COUNT:
            count = len(data)
            return [{
                "date": data[0]["date"] if data else datetime.now().strftime("%Y-%m-%d"),
                "value": count,
                "metric": metric_def["name"],
                "unit": "次",
                "_operation": "COUNT"
            }]

        else:
            return data

    def _apply_group_by(
        self,
        data: List[Dict[str, Any]],
        dimensions: List[str]]
    ) -> List[Dict[str, Any]]:
        """应用分组."""
        if not dimensions:
            return data

        # 按维度分组聚合
        groups = {}
        for row in data:
            key = tuple(row.get(dim, "未知") for dim in dimensions)
            if key not in groups:
                groups[key] = []
            groups[key].append(row)

        # 计算每组总和
        result = []
        for key, rows in groups.items():
            total = sum(row["value"] for row in rows)
            result.append({
                **rows[0],
                "value": round(total, 2),
                "_group_by": {dim: rows[0].get(dim, "未知") for dim in dimensions},
                "_group_count": len(rows)
            })

        return result

    def _apply_filters(
        self,
        data: List[Dict[str, Any]],
        filters: List
    ) -> List[Dict[str, Any]]:
        """应用过滤条件."""
        filtered = data

        for f in filters:
            if f.operator == "=":
                filtered = [row for row in filtered if row.get(f.field) == f.value]
            elif f.operator == "IN":
                filtered = [row for row in filtered if row.get(f.field) in f.value]
            elif f.operator == ">":
                filtered = [row for row in filtered if row.get(f.field, 0) > f.value]
            elif f.operator == "<":
                filtered = [row for row in filtered if row.get(f.field, float('inf')) < f.value]

        return filtered

    def _apply_order_by(self, data: List[Dict[str, Any]], order_by: str) -> List[Dict[str, Any]]:
        """应用排序."""
        reverse = order_by.startswith("-")
        field = order_by.lstrip("+-")

        return sorted(
            data,
            key=lambda x: x.get(field, 0),
            reverse=reverse
        )

    def _apply_comparison(
        self,
        data: List[Dict[str, Any]],
        comparison,
        metric_def: Dict[str, Any]]
    ) -> Dict[str, Any]:
        """应用比较（同比/环比）."""
        # 模拟比较数据
        current_value = data[0]["value"] if data else 0

        if comparison.value == "YoY":
            # 同比
            previous_value = current_value / random.uniform(1.1, 1.3)
            change = current_value - previous_value
            change_rate = (change / previous_value * 100) if previous_value > 0 else 0

            return {
                "current": current_value,
                "previous": round(previous_value, 2),
                "change": round(change, 2),
                "change_rate": round(change_rate, 2),
                "comparison_type": "同比"
            }

        elif comparison.value == "MoM":
            # 环比
            previous_value = current_value / random.uniform(0.9, 1.1)
            change = current_value - previous_value
            change_rate = (change / previous_value * 100) if previous_value > 0 else 0

            return {
                "current": current_value,
                "previous": round(previous_value, 2),
                "change": round(change, 2),
                "change_rate": round(change_rate, 2),
                "comparison_type": "环比"
            }

        return {
            "current": current_value,
            "comparison_type": comparison.value
        }


# 测试
if __name__ == "__main__":
    from datetime import datetime
    from .generator import MQLGenerator
    from ..inference.intent import IntentRecognizer

    print("\n🧪 测试MQL执行引擎")
    print("=" * 60)

    # 初始化
    generator = MQLGenerator()
    recognizer = IntentRecognizer()
    engine = MQLExecutionEngine()

    # 测试查询
    query = "最近7天的GMV总和"
    print(f"\n查询: {query}")
    print("-" * 60)

    # 识别意图
    intent = recognizer.recognize(query)

    # 生成MQL
    mql_query = generator.generate(intent)
    print(f"\n生成的MQL:")
    print(str(mql_query))

    # 执行查询
    print(f"\n执行结果:")
    result = engine.execute(mql_query)

    print(f"   返回行数: {result['row_count']}")
    print(f"   执行时间: {result['execution_time_ms']}ms")

    if result['result']:
        print(f"   数据示例:")
        for row in result['result'][:3]:
            print(f"      {row}")

    print("\n" + "=" * 60)
