"""意图识别模块."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class TimeGranularity(Enum):
    """时间粒度."""

    REALTIME = "realtime"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class AggregationType(Enum):
    """聚合类型."""

    SUM = "sum"  # 求和
    AVG = "avg"  # 平均
    COUNT = "count"  # 计数
    MAX = "max"  # 最大值
    MIN = "min"  # 最小值
    RATE = "rate"  # 比率
    RATIO = "ratio"  # 占比


@dataclass
class QueryIntent:
    """查询意图.

    Attributes:
        query: 原始查询
        core_query: 核心查询词（去除时间范围等）
        time_range: 时间范围 (start_date, end_date)
        time_granularity: 时间粒度
        aggregation_type: 聚合类型
        dimensions: 维度列表
        comparison_type: 比较类型 (yoy: 同比, qoq: 环比)
        filters: 过滤条件
    """

    query: str
    core_query: str
    time_range: Optional[tuple[datetime, datetime]]
    time_granularity: Optional[TimeGranularity]
    aggregation_type: Optional[AggregationType]
    dimensions: list[str]
    comparison_type: Optional[str]
    filters: dict[str, any]

    def __str__(self) -> str:
        """字符串表示."""
        parts = [f"查询: {self.query}"]

        if self.time_range:
            start, end = self.time_range
            parts.append(f"时间: {start.strftime('%Y-%m-%d')} 至 {end.strftime('%Y-%m-%d')}")
            if self.time_granularity:
                parts.append(f"({self.time_granularity.value})")

        if self.aggregation_type:
            parts.append(f"聚合: {self.aggregation_type.value}")

        if self.dimensions:
            parts.append(f"维度: {', '.join(self.dimensions)}")

        if self.comparison_type:
            parts.append(f"比较: {self.comparison_type}")

        return " | ".join(parts) if parts else self.query


class IntentRecognizer:
    """意图识别器."""

    # 时间范围正则模式
    TIME_PATTERNS = [
        # 相对时间
        (r'最近(\d+)[天日]', TimeGranularity.DAY, -1),
        (r'过去(\d+)[天日]', TimeGranularity.DAY, -1),
        (r'前(\d+)[天日]', TimeGranularity.DAY, -1),
        (r'近(\d+)[天日]', TimeGranularity.DAY, -1),
        (r'本[周个]周', TimeGranularity.WEEK, 0),
        (r'上个[周个]周', TimeGranularity.WEEK, -1),
        (r'本月', TimeGranularity.MONTH, 0),
        (r'上[个]月', TimeGranularity.MONTH, -1),
        (r'今年', TimeGranularity.YEAR, 0),
        (r'去年', TimeGranularity.YEAR, -1),
        # 绝对时间
        (r'(\d{4})年(\d{1,2})月', TimeGranularity.MONTH, None),
        (r'(\d{4})年', TimeGranularity.YEAR, None),
    ]

    # 聚合类型模式
    AGGREGATION_PATTERNS = [
        (r'总和|总计|合计|总[额度数]|汇总', AggregationType.SUM),
        (r'平均[值]?|人均', AggregationType.AVG),
        (r'计数|数量|个数|有多少', AggregationType.COUNT),
        (r'最高|最大|峰值', AggregationType.MAX),
        (r'最低|最小', AggregationType.MIN),
        (r'([增变]长)率|增长[幅度]度', AggregationType.RATE),
        (r'占比|比率|比例', AggregationType.RATIO),
    ]

    # 比较类型模式
    COMPARISON_PATTERNS = [
        (r'同比|year[- ]?over[- ]?year', 'yoy'),
        (r'环比|month[- ]?over[- ]?month', 'mom'),
        (r'日[环比]', 'dod'),
        (r'周[环比]', 'wow'),
    ]

    # 维度模式
    DIMENSION_PATTERNS = [
        r'按(用户|地区|品类|渠道)',
        r'(用户|地区|品类|渠道)',
    ]

    def __init__(self) -> None:
        """初始化意图识别器."""
        self.now = datetime.now()

    def recognize(self, query: str) -> QueryIntent:
        """识别查询意图.

        Args:
            query: 用户查询文本

        Returns:
            查询意图对象
        """
        query = query.strip()

        # 1. 识别时间范围
        time_range, granularity = self._extract_time_range(query)
        core_query = self._remove_time_info(query, time_range)

        # 2. 识别聚合类型
        agg_type = self._extract_aggregation_type(core_query)

        # 3. 识别维度
        dimensions = self._extract_dimensions(core_query)

        # 4. 识别比较类型
        comparison_type = self._extract_comparison_type(query)

        # 5. 提取过滤条件
        filters = self._extract_filters(query)

        return QueryIntent(
            query=query,
            core_query=core_query,
            time_range=time_range,
            time_granularity=granularity,
            aggregation_type=agg_type,
            dimensions=dimensions,
            comparison_type=comparison_type,
            filters=filters,
        )

    def _extract_time_range(
        self,
        query: str,
    ) -> tuple[Optional[tuple[datetime, datetime]], Optional[TimeGranularity]]:
        """提取时间范围.

        Args:
            query: 查询文本

        Returns:
            ((start_date, end_date), granularity)
        """
        for pattern, granularity, offset in self.TIME_PATTERNS:
            match = re.search(pattern, query)
            if match:
                offset_value = int(match.group(1)) if offset else 0

                if granularity == TimeGranularity.REALTIME:
                    return None, None

                if offset_value == 0:
                    # 本周、本月、今年 - 使用当前时间范围
                    start, end = self._get_current_period(granularity)
                    return (start, end), granularity
                else:
                    # 最近N天、过去N天、前N天
                    end = self.now
                    start = end - timedelta(days=offset_value)
                    return (start, end), granularity

                # 绝对时间处理
                if "年" in pattern:
                    year = int(match.group(1))
                    month = int(match.group(2)) if match.lastindex >= 3 else None

                    if month:
                        start = datetime(year, month, 1)
                        # 下个月的第一天
                        if month == 12:
                            end = datetime(year + 1, 1, 1)
                        else:
                            end = datetime(year, month + 1, 1)
                        # 一天前作为结束
                        end = end - timedelta(days=1)
                        return (start, end), granularity
                    else:
                        start = datetime(year, 1, 1)
                        end = datetime(year + 1, 1, 1)
                        return (start, end), granularity

        return None, None

    def _get_current_period(
        self,
        granularity: TimeGranularity,
    ) -> tuple[datetime, datetime]:
        """获取当前时间范围.

        Args:
            granularity: 时间粒度

        Returns:
            (start_date, end_date)
        """
        now = self.now

        if granularity == TimeGranularity.WEEK:
            # 本周（周一到周日）
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=6)
            end = end.replace(hour=23, minute=59, second=59)
            return start, end

        elif granularity == TimeGranularity.MONTH:
            # 本月
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # 下个月第一天
            if start.month == 12:
                end = datetime(start.year + 1, 1, 1)
            else:
                end = datetime(start.year, start.month + 1, 1)
            end = end - timedelta(days=1)
            return start, end

        elif granularity == TimeGranularity.QUARTER:
            # 本季度
            quarter = (now.month - 1) // 3 + 1
            start = datetime(now.year, (quarter - 1) * 3 + 1, 1)
            if quarter == 4:
                end = datetime(now.year + 1, 1, 1)
            else:
                end = datetime(now.year, quarter * 3 + 1, 1)
            end = end - timedelta(days=1)
            return start, end

        elif granularity == TimeGranularity.YEAR:
            # 今年
            start = datetime(now.year, 1, 1)
            end = datetime(now.year + 1, 1, 1)
            end = end - timedelta(days=1)
            return start, end

        else:
            # 默认：最近30天
            start = now - timedelta(days=30)
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start, end

    def _remove_time_info(
        self,
        query: str,
        time_range: Optional[tuple[datetime, datetime]],
    ) -> str:
        """移除时间相关的信息，提取核心查询词.

        Args:
            query: 原始查询
            time_range: 时间范围

        Returns:
            核心查询词
        """
        if not time_range:
            return query

        # 移除已识别的时间模式
        core_query = query
        for pattern, _, _ in self.TIME_PATTERNS:
            core_query = re.sub(pattern, '', core_query)

        # 清理多余空格
        core_query = ' '.join(core_query.split())

        return core_query

    def _extract_aggregation_type(self, query: str) -> Optional[AggregationType]:
        """提取聚合类型.

        Args:
            query: 查询文本

        Returns:
            聚合类型
        """
        for pattern, agg_type in self.AGGREGATION_PATTERNS:
            if re.search(pattern, query):
                return agg_type

        return None

    def _extract_dimensions(self, query: str) -> list[str]:
        """提取维度信息.

        Args:
            query: 查询文本

        Returns:
            维度列表
        """
        dimensions = []

        for pattern in self.DIMENSION_PATTERNS:
            match = re.search(pattern, query)
            if match:
                dimension = match.group(1) if match.lastindex >= 1 else None
                if dimension:
                    dimensions.append(dimension)

        return dimensions

    def _extract_comparison_type(self, query: str) -> Optional[str]:
        """提取比较类型.

        Args:
            query: 查询文本

        Returns:
            比较类型代码
        """
        for pattern, comp_type in self.COMPARISON_PATTERNS:
            if re.search(pattern, query):
                return comp_type

        return None

    def _extract_filters(self, query: str) -> dict[str, any]:
        """提取过滤条件.

        Args:
            query: 查询文本

        Returns:
            过滤条件字典
        """
        filters = {}

        # 示例：识别特定的业务域
        if '电商' in query:
            filters['domain'] = '电商'
        elif '用户' in query:
            filters['domain'] = '用户'
        elif '营收' in query or '收入' in query:
            filters['domain'] = '营收'

        # 示例：识别数据新鲜度要求
        if '实时' in query:
            filters['freshness'] = 'realtime'
        elif '历史' in query:
            filters['freshness'] = 'historical'

        return filters
