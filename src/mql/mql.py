"""MQL - Metric Query Language (指标查询语言).

MQL是一种用于查询和分析业务指标的DSL（领域特定语言）。

语法示例:
1. 简单查询:
   SELECT GMV

2. 带时间范围:
   SELECT GMV FROM 2024-01-01 TO 2024-01-31

3. 带聚合:
   SELECT SUM(GMV) GROUP BY 地区

4. 带过滤:
   SELECT GMV WHERE 地区 = '华东'

5. 复杂查询:
   SELECT SUM(GMV)
   FROM 2024-01-01 TO 2024-01-31
   GROUP BY 地区, 品类
   WHERE 地区 IN ('华东', '华南')

6. 同比查询:
   SELECT GMV COMPARE WITH PREVIOUS_PERIOD

7. 根因分析:
   ANALYZE GMV WHERE GMV < 100000
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, List
from enum import Enum


class MetricOperator(Enum):
    """指标操作符."""
    SELECT = "SELECT"
    SUM = "SUM"
    AVG = "AVG"
    COUNT = "COUNT"
    MAX = "MAX"
    MIN = "MIN"
    RATE = "RATE"
    RATIO = "RATIO"


class ComparisonType(Enum):
    """比较类型."""
    YOY = "YoY"  # 同比
    MOM = "MoM"  # 环比
    WOW = "WoW"  # 周环比
    DOD = "DoD"  # 日环比
    TARGET = "TARGET"  # 目标值对比


@dataclass
class TimeRange:
    """时间范围."""
    start: datetime
    end: datetime
    granularity: str = "day"  # day, week, month, quarter, year


@dataclass
class Filter:
    """过滤条件."""
    field: str
    operator: str  # =, !=, >, <, IN, NOT IN
    value: Any


@dataclass
class GroupBy:
    """分组维度."""
    dimensions: List[str]


@dataclass
class MQLQuery:
    """MQL查询."""

    # 查询的指标
    metric: str
    operator: MetricOperator = MetricOperator.SELECT

    # 时间范围
    time_range: Optional[TimeRange] = None

    # 维度分组
    group_by: Optional[GroupBy] = None

    # 过滤条件
    filters: List[Filter] = field(default_factory=list)

    # 比较类型
    comparison: Optional[ComparisonType] = None

    # 排序
    order_by: Optional[str] = None
    order_limit: Optional[int] = None

    # 根因分析模式
    is_analysis: bool = False
    analysis_threshold: Optional[float] = None

    def to_dict(self) -> dict:
        """转换为字典格式."""
        return {
            "metric": self.metric,
            "operator": self.operator.value if isinstance(self.operator, MetricOperator) else self.operator,
            "time_range": {
                "start": self.time_range.start.isoformat() if self.time_range else None,
                "end": self.time_range.end.isoformat() if self.time_range else None,
                "granularity": self.time_range.granularity if self.time_range else None
            } if self.time_range else None,
            "group_by": {
                "dimensions": self.group_by.dimensions
            } if self.group_by else None,
            "filters": [
                {"field": f.field, "operator": f.operator, "value": f.value}
                for f in self.filters
            ] if self.filters else None,
            "comparison": self.comparison.value if self.comparison else None,
            "order_by": self.order_by,
            "limit": self.order_limit,
            "is_analysis": self.is_analysis,
            "analysis_threshold": self.analysis_threshold
        }

    def __str__(self) -> str:
        """转换为MQL字符串."""
        parts = []

        # SELECT子句
        if self.operator == MetricOperator.SELECT:
            parts.append(f"SELECT {self.metric}")
        else:
            parts.append(f"SELECT {self.operator.value}({self.metric})")

        # FROM子句（时间范围）
        if self.time_range:
            parts.append(
                f"FROM {self.time_range.start.strftime('%Y-%m-%d')} "
                f"TO {self.time_range.end.strftime('%Y-%m-%d')}"
            )

        # GROUP BY子句
        if self.group_by:
            dims = ", ".join(self.group_by.dimensions)
            parts.append(f"GROUP BY {dims}")

        # WHERE子句
        if self.filters:
            conditions = []
            for f in self.filters:
                if f.operator == "IN":
                    values = ", ".join(f"'{v}'" for v in f.value)
                    conditions.append(f"{f.field} IN ({values})")
                else:
                    conditions.append(f"{f.field} {f.operator} {f.value}")
            parts.append(f"WHERE {' AND '.join(conditions)}")

        # COMPARE子句
        if self.comparison:
            parts.append(f"COMPARE WITH {self.comparison.value}")

        # ORDER BY子句
        if self.order_by:
            parts.append(f"ORDER BY {self.order_by}")

        if self.order_limit:
            parts.append(f"LIMIT {self.order_limit}")

        # ANALYZE子句
        if self.is_analysis:
            parts.append("ANALYZE ROOT CAUSE")
            if self.analysis_threshold:
                parts.append(f"WHERE {self.metric} < {self.analysis_threshold}")

        return "\n".join(parts)


# 示例用法
if __name__ == "__main__":
    # 示例1: 简单查询
    query1 = MQLQuery(metric="GMV")
    print("示例1 - 简单查询:")
    print(query1)
    print()

    # 示例2: 带时间范围和聚合
    query2 = MQLQuery(
        metric="GMV",
        operator=MetricOperator.SUM,
        time_range=TimeRange(
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 31),
            granularity="day"
        )
    )
    print("示例2 - 时间范围查询:")
    print(query2)
    print()

    # 示例3: 带分组和过滤
    query3 = MQLQuery(
        metric="GMV",
        operator=MetricOperator.SUM,
        time_range=TimeRange(
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 31)
        ),
        group_by=GroupBy(dimensions=["地区", "品类"]),
        filters=[
            Filter(field="地区", operator="IN", value=["华东", "华南"])
        ]
    )
    print("示例3 - 复杂查询:")
    print(query3)
    print()

    # 示例4: 同比查询
    query4 = MQLQuery(
        metric="GMV",
        time_range=TimeRange(
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 31)
        ),
        comparison=ComparisonType.YOY
    )
    print("示例4 - 同比查询:")
    print(query4)
    print()

    # 示例5: 根因分析
    query5 = MQLQuery(
        metric="GMV",
        is_analysis=True,
        analysis_threshold=100000
    )
    print("示例5 - 根因分析:")
    print(query5)
