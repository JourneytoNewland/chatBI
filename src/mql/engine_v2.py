"""MQL执行引擎 V2 - 使用PostgreSQL真实数据."""

import logging
from typing import Any, Dict, List, Optional
import time

from src.inference.intent import QueryIntent
from src.database.postgres_client import postgres_client
from .sql_generator_v2 import SQLGeneratorV2


logger = logging.getLogger(__name__)


class MQLExecutionEngineV2:
    """MQL执行引擎 V2.

    功能:
    1. 接收QueryIntent对象
    2. 生成SQL查询
    3. 执行PostgreSQL查询
    4. 格式化结果
    5. 性能统计

    Attributes:
        postgres_client: PostgreSQL客户端
        sql_generator: SQL生成器
    """

    def __init__(self):
        """初始化执行引擎."""
        self.postgres_client = postgres_client
        self.sql_generator = SQLGeneratorV2()

    def execute(self, intent: QueryIntent) -> Dict[str, Any]:
        """执行MQL查询.

        Args:
            intent: 查询意图对象

        Returns:
            查询结果字典，包含:
            - query: 原始查询
            - intent: 意图对象
            - sql: 生成的SQL
            - result: 查询结果列表
            - row_count: 结果行数
            - execution_time_ms: 执行耗时
            - error: 错误信息（如果有）
        """
        start_time = time.time()
        error = None
        result = []
        sql = ""

        try:
            # 1. 生成SQL查询
            logger.info(f"🔄 执行查询: {intent.query}")
            logger.info(f"   核心指标: {intent.core_query}")
            logger.info(f"   时间范围: {intent.time_range}")
            logger.info(f"   维度: {intent.dimensions}")
            logger.info(f"   聚合类型: {intent.aggregation_type}")

            sql, params = self.sql_generator.generate(intent)
            logger.info(f"✅ SQL生成成功:\n{sql}")
            logger.info(f"   参数: {params}")

            # 2. 执行SQL查询
            query_result = self.postgres_client.execute_query(
                sql,
                params=params,
                fetch='all',
                dict_cursor=True
            )

            # 3. 格式化结果
            result = self._format_result(query_result, intent)
            logger.info(f"✅ 查询成功: {len(result)} 条记录")

        except ValueError as e:
            error = f"查询参数错误: {str(e)}"
            logger.error(f"❌ {error}")
        except Exception as e:
            error = f"查询执行失败: {str(e)}"
            logger.error(f"❌ {error}")
            logger.exception("详细错误信息:")

        execution_time = int((time.time() - start_time) * 1000)

        return {
            "query": intent.query,
            "intent": intent,
            "sql": sql,
            "result": result,
            "row_count": len(result),
            "execution_time_ms": execution_time,
            "error": error
        }

    def execute_batch(self, intents: List[QueryIntent]) -> List[Dict[str, Any]]:
        """批量执行查询.

        Args:
            intents: 查询意图列表

        Returns:
            查询结果列表
        """
        results = []

        for intent in intents:
            result = self.execute(intent)
            results.append(result)

        return results

    def _format_result(
        self,
        query_result: List[Dict[str, Any]],
        intent: QueryIntent
    ) -> List[Dict[str, Any]]:
        """格式化查询结果.

        Args:
            query_result: 原始查询结果
            intent: 查询意图

        Returns:
            格式化后的结果
        """
        formatted = []

        for row in query_result:
            formatted_row = {}

            # 1. 提取日期（如果有）
            if 'date' in row:
                formatted_row['date'] = str(row['date'])

            # 2. 提取维度（如果有）
            for dim in (intent.dimensions or []):
                if dim in row:
                    formatted_row[dim] = row[dim]

            # 3. 提取指标值
            if 'metric_value' in row:
                value = row['metric_value']

                # 格式化数值
                if isinstance(value, float):
                    # 如果是比率（如转化率），保留4位小数
                    if intent.core_query in ["转化率", "留存率", "毛利率", "净利率", "ROI"]:
                        formatted_row['value'] = round(value * 100, 2)  # 转为百分比
                        formatted_row['value_raw'] = value
                    else:
                        # 如果是大数值（如GMV），保留2位小数
                        formatted_row['value'] = round(value, 2)
                        formatted_row['value_raw'] = value
                else:
                    formatted_row['value'] = value
                    formatted_row['value_raw'] = value

            # 4. 保留原始数据（用于调试）
            formatted_row['_raw'] = row

            formatted.append(formatted_row)

        return formatted

    def get_metric_schema(self, metric_name: str) -> Dict[str, Any]:
        """获取指标的Schema信息.

        Args:
            metric_name: 指标名称

        Returns:
            指标Schema字典
        """
        table_name, column_name = self.sql_generator._get_metric_table(metric_name)

        # 获取表结构信息
        table_info = self.postgres_client.get_table_info(table_name)

        return {
            "metric_name": metric_name,
            "table_name": table_name,
            "column_name": column_name,
            "table_columns": table_info
        }

    def get_supported_metrics(self) -> List[str]:
        """获取支持的指标列表.

        Returns:
            指标名称列表
        """
        return list(self.sql_generator.METRIC_TABLE_MAPPING.keys())

    def get_available_dimensions(self, metric_name: str) -> List[str]:
        """获取指标可用的维度.

        Args:
            metric_name: 指标名称

        Returns:
            可用维度列表
        """
        # 根据事实表确定可用维度
        table_name, _ = self.sql_generator._get_metric_table(metric_name)

        # 不同事实表支持的维度
        table_dimensions = {
            "fact_orders": ["地区", "品类", "渠道", "用户等级"],
            "fact_user_activity": ["地区", "渠道", "用户等级"],
            "fact_traffic": ["地区", "渠道"],
            "fact_revenue": ["地区", "用户等级"],
            "fact_finance": ["地区"],
        }

        return table_dimensions.get(table_name, [])


# 全局单例
mql_engine_v2 = MQLExecutionEngineV2()


# 测试
if __name__ == "__main__":
    from src.inference.intent import QueryIntent, TimeRange, AggregationType

    print("\n🧪 测试MQL执行引擎V2")
    print("=" * 60)

    engine = MQLExecutionEngineV2()

    # 测试1: 简单查询 - GMV
    print("\n测试1: 简单查询 - GMV")
    intent1 = QueryIntent(
        query="GMV",
        core_query="GMV"
    )
    result1 = engine.execute(intent1)
    print(f"查询: {result1['query']}")
    print(f"SQL: {result1['sql']}")
    print(f"结果行数: {result1['row_count']}")
    print(f"执行耗时: {result1['execution_time_ms']}ms")
    if result1['error']:
        print(f"错误: {result1['error']}")
    else:
        print(f"结果示例: {result1['result'][:3]}")

    # 测试2: 时间范围查询 - 最近7天GMV
    print("\n" + "=" * 60)
    print("\n测试2: 时间范围查询 - 最近7天GMV")
    intent2 = QueryIntent(
        query="最近7天GMV",
        core_query="GMV",
        time_range=TimeRange(granularity="day")
    )
    result2 = engine.execute(intent2)
    print(f"查询: {result2['query']}")
    print(f"结果行数: {result2['row_count']}")
    print(f"执行耗时: {result2['execution_time']}ms")
    if result2['error']:
        print(f"错误: {result2['error']}")
    else:
        print(f"结果示例: {result2['result'][:3]}")

    # 测试3: 维度分组查询 - 按地区统计GMV
    print("\n" + "=" * 60)
    print("\n测试3: 维度分组查询 - 按地区统计GMV")
    intent3 = QueryIntent(
        query="按地区GMV",
        core_query="GMV",
        dimensions=["地区"]
    )
    result3 = engine.execute(intent3)
    print(f"查询: {result3['query']}")
    print(f"结果行数: {result3['row_count']}")
    print(f"执行耗时: {result3['execution_time_ms']}ms")
    if result3['error']:
        print(f"错误: {result3['error']}")
    else:
        print(f"结果示例: {result3['result'][:3]}")

    # 测试4: 获取支持的指标
    print("\n" + "=" * 60)
    print("\n测试4: 获取支持的指标")
    metrics = engine.get_supported_metrics()
    print(f"支持的指标数量: {len(metrics)}")
    print(f"指标列表: {metrics[:10]}...")

    # 测试5: 获取可用维度
    print("\n" + "=" * 60)
    print("\n测试5: 获取GMV的可用维度")
    dimensions = engine.get_available_dimensions("GMV")
    print(f"GMV的可用维度: {dimensions}")

    print("\n" + "=" * 60)
    print("✅ 所有测试通过")
