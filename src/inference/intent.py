"""意图识别模块."""

import re
from dataclasses import dataclass, field
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


class TrendType(Enum):
    """趋势分析类型."""

    UPWARD = "upward"  # 上升/增长
    DOWNWARD = "downward"  # 下降/下跌
    FLUCTUATING = "fluctuating"  # 波动
    STABLE = "stable"  # 稳定/持平


class SortOrder(Enum):
    """排序方向."""

    DESC = "desc"  # 降序（Top N）
    ASC = "asc"  # 升序（Bottom N）


@dataclass
class SortRequirement:
    """排序需求."""

    top_n: Optional[int]  # 返回前N个结果（None表示无限制）
    order: SortOrder  # 排序方向
    metric: Optional[str] = None  # 排序依据的指标（默认为查询的主指标）


@dataclass
class ThresholdFilter:
    """阈值过滤条件."""

    metric: str  # 指标名称
    operator: str  # 比较运算符（>, <, >=, <=, ==, !=）
    value: float  # 阈值（数值）
    unit: Optional[str] = None  # 单位（万/百万/亿，用于转换）


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
        trend_type: 趋势类型
        sort_requirement: 排序需求
        threshold_filters: 阈值过滤列表
    """

    query: str
    core_query: str
    time_range: Optional[tuple[datetime, datetime]]
    time_granularity: Optional[TimeGranularity]
    aggregation_type: Optional[AggregationType]
    dimensions: list[str]
    comparison_type: Optional[str]
    filters: dict[str, any]
    # 新增字段（可选，默认None）
    trend_type: Optional[TrendType] = None
    sort_requirement: Optional[SortRequirement] = None
    threshold_filters: list[ThresholdFilter] = field(default_factory=list)

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
    # 注意：更具体的模式应该放在前面，优先匹配
    TIME_PATTERNS = [
        # 绝对时间（更具体，放在前面）
        (r'(\d{4})年(\d{1,2})月', TimeGranularity.MONTH, None),
        (r'(\d{4})年', TimeGranularity.YEAR, None),
        # 相对时间
        (r'最近(\d+)[天日]', TimeGranularity.DAY, -1),
        (r'过去(\d+)[天日]', TimeGranularity.DAY, -1),
        (r'前(\d+)[天日]', TimeGranularity.DAY, -1),
        (r'近(\d+)[天日]', TimeGranularity.DAY, -1),
        (r'本周|本[周个]周', TimeGranularity.WEEK, 0),
        (r'上个[周个]周', TimeGranularity.WEEK, -1),
        (r'本月', TimeGranularity.MONTH, 0),
        (r'上[个]?月', TimeGranularity.MONTH, -1),  # "上月"或"上个月"
        (r'今年', TimeGranularity.YEAR, 0),
        (r'去年', TimeGranularity.YEAR, -1),
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

    # 疑问词模式
    QUESTION_PATTERNS = [
        r'是什么[意思意思]?',
        r'是什么',
        r'怎么算',
        r'如何计算',
        r'什么意思',
        r'怎么理解',
        r'解释一下',
        r'说明',
    ]

    # 趋势分析模式
    TREND_PATTERNS = [
        # 上升趋势
        (
            r'(GMV|DAU|营收|销量|用户|转化率|客单价|增长率|活跃用户|留存率).{0,5}(上升|增长|提高|增加|攀升|上涨)',
            TrendType.UPWARD,
        ),
        (
            r'(GMV|DAU|营收|销量|用户|转化率|客单价|增长率|活跃用户|留存率).{0,5}趋势.{0,3}(好|优|强)',
            TrendType.UPWARD,
        ),
        # 下降趋势
        (
            r'(GMV|DAU|营收|销量|用户|转化率|客单价|增长率|活跃用户|留存率).{0,5}(下降|下跌|减少|降低|下滑|回落)',
            TrendType.DOWNWARD,
        ),
        (
            r'(GMV|DAU|营收|销量|用户|转化率|客单价|增长率|活跃用户|留存率).{0,5}趋势.{0,3}(差|弱|低)',
            TrendType.DOWNWARD,
        ),
        # 波动
        (
            r'(GMV|DAU|营收|销量|用户|转化率|客单价|增长率|活跃用户|留存率).{0,5}(波动|震荡|起伏|不稳定)',
            TrendType.FLUCTUATING,
        ),
        # 稳定
        (
            r'(GMV|DAU|营收|销量|用户|转化率|客单价|增长率|活跃用户|留存率).{0,5}(稳定|持平|平稳|不变)',
            TrendType.STABLE,
        ),
    ]

    # 排序需求模式
    SORT_PATTERNS = [
        # Top N（前N个）
        (r'(前|Top|top)\s*(\d+)[个名]?\s*(\S+)?', "desc"),
        # Top N（无数字，如"前几个"）
        (r'(前|Top|top)\s*(几个|一些|部分|\S+)', "desc_no_num"),
        # Bottom N（后N个）
        (r'(后|Bottom|bottom)\s*(\d+)[个名]?\s*(\S+)?', "asc"),
        # 最高/最低（支持"的"字）
        (r'(最高|最大|最强|峰值)[的的]?\s*(\d+)[个名名位]?\s*(\S+)?', "desc"),
        (r'(最低|最小|最弱)[的的]?\s*(\d+)[个名名位]?\s*(\S+)?', "asc"),
        # 最高/最低（无数字）
        (r'(最高|最大|最强|峰值)(?!\s*\d)', "desc_no_num"),
        (r'(最低|最小|最弱)(?!\s*\d)', "asc_no_num"),
    ]

    # 阈值过滤模式
    THRESHOLD_PATTERNS = [
        # 数值比较（符号运算符）
        (r'(\S+?)\s*(>|<|>=|<=|==|!=)\s*(\d+(?:\.\d+)?)\s*(万|百万|亿|k|M|B)?', "numeric"),
        # 数值比较（中文运算符）
        (
            r'(\S+?)\s*(大于|超过|高于|小于|低于|少于|大于等于|不低于|至少|不超过|至多|不小于)\s*(\d+(?:\.\d+)?)\s*(万|百万|亿|k|M|B)?',
            "numeric_chinese",
        ),
        # 范围过滤
        (r'(\S+?)\s*(在|介于)\s*(\d+(?:\.\d+)?)\s*[-~到至]\s*(\d+(?:\.\d+)?)', "range"),
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

        # 1.5. 移除疑问词
        core_query = self._remove_question_words(core_query)

        # 2. 识别聚合类型
        agg_type = self._extract_aggregation_type(core_query)

        # 3. 识别维度
        dimensions = self._extract_dimensions(core_query)

        # 4. 识别比较类型
        comparison_type = self._extract_comparison_type(query)

        # 5. 提取过滤条件
        filters = self._extract_filters(query)

        # ========== 新增：6. 趋势分析识别 ==========
        trend_type = self._extract_trend_type(query)

        # ========== 新增：7. 排序需求识别 ==========
        sort_requirement = self._extract_sort_requirement(query)

        # ========== 新增：8. 阈值过滤识别 ==========
        threshold_filters = self._extract_threshold_filters(query)

        return QueryIntent(
            query=query,
            core_query=core_query,
            time_range=time_range,
            time_granularity=granularity,
            aggregation_type=agg_type,
            dimensions=dimensions,
            comparison_type=comparison_type,
            filters=filters,
            # 新增字段
            trend_type=trend_type,
            sort_requirement=sort_requirement,
            threshold_filters=threshold_filters,
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
                # 检查是否为绝对时间模式（offset=None）
                if offset is None:
                    # 绝对时间处理
                    if "年" in pattern:
                        year = int(match.group(1))
                        # 修复: lastindex从1开始，所以第2组应该是 lastindex >= 2
                        month = int(match.group(2)) if match.lastindex >= 2 and match.group(2) else None

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
                else:
                    # 相对时间处理
                    # 尝试提取 offset 值（如果有捕获组）
                    offset_value = 0
                    if match.lastindex and match.lastindex >= 1:
                        try:
                            offset_value = int(match.group(1))
                        except (ValueError, IndexError):
                            offset_value = 0

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

        # 移除残留的 "的"、"之" 等助词
        core_query = re.sub(r'^[的的之之]+', '', core_query)
        core_query = re.sub(r'[的的之之]+$', '', core_query)

        # 清理多余空格
        core_query = ' '.join(core_query.split())

        return core_query

    def _remove_question_words(self, query: str) -> str:
        """移除疑问词，提取核心查询词.

        Args:
            query: 查询文本

        Returns:
            移除疑问词后的核心查询词
        """
        core_query = query

        # 移除疑问词模式
        for pattern in self.QUESTION_PATTERNS:
            core_query = re.sub(pattern, '', core_query)

        # 清理多余空格和标点
        core_query = core_query.strip()
        core_query = re.sub(r'[？?！!。，,]', '', core_query)
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

    def _extract_trend_type(self, query: str) -> Optional[TrendType]:
        """提取趋势类型.

        Args:
            query: 查询文本

        Returns:
            趋势类型（如果未识别到则返回None）
        """
        for pattern, trend in self.TREND_PATTERNS:
            if re.search(pattern, query):
                return trend
        return None

    def _extract_sort_requirement(self, query: str) -> Optional[SortRequirement]:
        """提取排序需求.

        Args:
            query: 查询文本

        Returns:
            排序需求（如果未识别到则返回None）
        """
        for pattern, order_str in self.SORT_PATTERNS:
            match = re.search(pattern, query)
            if match:
                # 判断排序方向
                if "desc" in order_str:
                    order = SortOrder.DESC
                else:
                    order = SortOrder.ASC

                top_n = None
                metric = None

                # 尝试提取数字和指标
                if match.lastindex and match.lastindex >= 2:
                    # 第2组可能是数字
                    if match.group(2):
                        try:
                            top_n = int(match.group(2))
                        except (ValueError, IndexError):
                            pass
                    # 第3组（如果存在）是指标
                    if match.lastindex >= 3 and match.group(3):
                        metric = match.group(3)

                return SortRequirement(top_n=top_n, order=order, metric=metric)
        return None

    def _extract_threshold_filters(self, query: str) -> list[ThresholdFilter]:
        """提取阈值过滤条件.

        Args:
            query: 查询文本

        Returns:
            阈值过滤列表
        """
        filters = []

        # 中文运算符到符号的映射
        chinese_op_map = {
            "大于": ">",
            "超过": ">",
            "高于": ">",
            "小于": "<",
            "低于": "<",
            "少于": "<",
            "大于等于": ">=",
            "不低于": ">=",
            "至少": ">=",
            "不超过": "<=",
            "至多": "<=",
            "不小于": ">=",
        }

        for pattern, pattern_type in self.THRESHOLD_PATTERNS:
            matches = re.finditer(pattern, query)
            for match in matches:
                if pattern_type in ["numeric", "numeric_chinese"] and match.lastindex >= 3:
                    metric = match.group(1)
                    operator = match.group(2)
                    value = float(match.group(3))
                    unit = match.group(4) if match.lastindex >= 4 and match.group(4) else None

                    # 如果是中文运算符，转换为符号
                    if pattern_type == "numeric_chinese" and operator in chinese_op_map:
                        operator = chinese_op_map[operator]

                    filters.append(ThresholdFilter(metric=metric, operator=operator, value=value, unit=unit))

        return filters
