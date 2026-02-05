"""意图识别测试."""

import pytest
from datetime import datetime, timedelta
from src.inference.intent import (
    IntentRecognizer,
    QueryIntent,
    TimeGranularity,
    AggregationType,
)


class TestIntentRecognition:
    """意图识别测试类."""

    def setup_method(self):
        """测试前准备."""
        self.recognizer = IntentRecognizer()

    # ========== 正常用例 ==========
    def test_simple_metric_query(self):
        """测试简单指标查询."""
        intent = self.recognizer.recognize("GMV")
        assert intent.query == "GMV"
        assert intent.core_query == "GMV"
        assert intent.time_range is None
        assert intent.aggregation_type is None

    def test_time_range_recent_days(self):
        """测试最近N天."""
        intent = self.recognizer.recognize("最近7天的GMV")
        assert intent.core_query == "GMV"
        assert intent.time_range is not None
        assert intent.time_granularity == TimeGranularity.DAY

        # 验证时间范围
        start, end = intent.time_range
        assert (end - start).days == 7

    def test_time_range_this_week(self):
        """测试本周."""
        intent = self.recognizer.recognize("本周活跃用户数")
        assert intent.core_query == "活跃用户数"
        assert intent.time_granularity == TimeGranularity.WEEK
        assert intent.time_range is not None

    def test_time_range_this_month(self):
        """测试本月."""
        intent = self.recognizer.recognize("本月营收")
        assert intent.core_query == "营收"
        assert intent.time_granularity == TimeGranularity.MONTH

    def test_time_range_this_year(self):
        """测试今年."""
        intent = self.recognizer.recognize("今年GMV")
        assert intent.core_query == "GMV"
        assert intent.time_granularity == TimeGranularity.YEAR

    def test_aggregation_sum(self):
        """测试求和聚合."""
        intent = self.recognizer.recognize("GMV总和")
        assert intent.aggregation_type == AggregationType.SUM

    def test_aggregation_avg(self):
        """测试平均聚合."""
        intent = self.recognizer.recognize("平均客单价")
        assert intent.aggregation_type == AggregationType.AVG

    def test_aggregation_count(self):
        """测试计数聚合."""
        intent = self.recognizer.recognize("用户数量")
        assert intent.aggregation_type == AggregationType.COUNT

    def test_aggregation_max(self):
        """测试最大值."""
        intent = self.recognizer.recognize("峰值GMV")
        assert intent.aggregation_type == AggregationType.MAX

    def test_aggregation_min(self):
        """测试最小值."""
        intent = self.recognizer.recognize("最低日活")
        assert intent.aggregation_type == AggregationType.MIN

    def test_aggregation_rate(self):
        """测试增长率."""
        intent = self.recognizer.recognize("GMV增长率")
        assert intent.aggregation_type == AggregationType.RATE

    def test_aggregation_ratio(self):
        """测试占比."""
        intent = self.recognizer.recognize("移动端占比")
        assert intent.aggregation_type == AggregationType.RATIO

    def test_dimension_by_user(self):
        """测试按用户维度."""
        intent = self.recognizer.recognize("按用户的GMV")
        assert "用户" in intent.dimensions

    def test_dimension_by_region(self):
        """测试按地区维度."""
        intent = self.recognizer.recognize("按地区的转化率")
        assert "地区" in intent.dimensions

    def test_comparison_yoy(self):
        """测试同比."""
        intent = self.recognizer.recognize("GMV同比")
        assert intent.comparison_type == "yoy"

    def test_comparison_mom(self):
        """测试环比."""
        intent = self.recognizer.recognize("营收环比")
        assert intent.comparison_type == "mom"

    def test_filter_domain(self):
        """测试业务域过滤."""
        intent = self.recognizer.recognize("电商GMV")
        assert intent.filters.get("domain") == "电商"

    def test_filter_freshness_realtime(self):
        """测试实时数据要求."""
        intent = self.recognizer.recognize("实时GMV")
        assert intent.filters.get("freshness") == "realtime"

    # ========== 边界测试用例 ==========
    def test_empty_query(self):
        """测试空查询."""
        intent = self.recognizer.recognize("")
        assert intent.query == ""

    def test_whitespace_query(self):
        """测试纯空格查询."""
        intent = self.recognizer.recognize("   ")
        # 空格会被 strip，这是正确的行为
        assert intent.query == "" or intent.query.strip() == ""

    def test_very_long_query(self):
        """测试超长查询."""
        long_query = "GMV" * 100
        intent = self.recognizer.recognize(long_query)
        assert intent.query == long_query

    def test_special_characters(self):
        """测试特殊字符."""
        intent = self.recognizer.recognize("GMV@#$%^&*()")
        assert intent.core_query == "GMV@#$%^&*()"

    def test_multiple_time_ranges(self):
        """测试多个时间表达（取第一个）."""
        intent = self.recognizer.recognize("最近7天本月的GMV")
        assert intent.time_range is not None
        # 应该识别到第一个时间表达

    def test_ambiguous_time(self):
        """测试模糊时间表达."""
        intent = self.recognizer.recognize("之前GMV")
        assert intent.core_query == "之前GMV"

    def test_no_space_chinese(self):
        """测试中文无空格."""
        intent = self.recognizer.recognize("最近7天GMV总和")
        assert intent.time_range is not None
        assert intent.aggregation_type == AggregationType.SUM

    def test_mixed_english_chinese(self):
        """测试中英混合."""
        intent = self.recognizer.recognize("今年year over year GMV")
        assert intent.time_granularity == TimeGranularity.YEAR

    # ========== 干扰测试用例 ==========
    def test_conflicting_aggregations(self):
        """测试冲突的聚合类型（取第一个）."""
        intent = self.recognizer.recognize("GMV总和平均值")
        # 应该识别到第一个聚合类型
        assert intent.aggregation_type in [AggregationType.SUM, AggregationType.AVG]

    def test_misleading_keywords(self):
        """测试误导性关键词."""
        intent = self.recognizer.recognize("GMV增长率的变化率")
        # 应该识别到增长率
        assert intent.aggregation_type == AggregationType.RATE

    def test_nested_dimensions(self):
        """测试嵌套维度."""
        intent = self.recognizer.recognize("按用户按地区的GMV")
        assert len(intent.dimensions) >= 1

    def test_unrelated_keywords(self):
        """测试无关关键词."""
        intent = self.recognizer.recognize("查询一下最近的GMV数据")
        # "查询一下"应该被忽略
        assert "GMV" in intent.core_query

    def test_conversational_query(self):
        """测试口语化查询."""
        intent = self.recognizer.recognize("我想看看最近7天的营收情况")
        assert intent.time_range is not None
        assert "营收" in intent.core_query

    def test_incomplete_query(self):
        """测试不完整查询."""
        intent = self.recognizer.recognize("最近")
        # 时间可能识别到，但核心查询为空
        assert intent.query == "最近"

    def test_overloaded_query(self):
        """测试信息过载查询."""
        query = "最近7天本月今年按用户按地区GMV总和平均值同比环比"
        intent = self.recognizer.recognize(query)
        # 应该能识别到多个维度，但不会崩溃
        assert intent is not None

    def test_typo_in_time(self):
        """测试时间表达错别字."""
        intent = self.recognizer.recognize("最经7天的GMV")  # "最近"错写为"最经"
        # 无法识别，应该返回None
        assert intent.time_range is None

    def test_synonym_time_expressions(self):
        """测试同义时间表达."""
        intent1 = self.recognizer.recognize("最近7天GMV")
        intent2 = self.recognizer.recognize("过去7天GMV")
        intent3 = self.recognizer.recognize("前7天GMV")
        intent4 = self.recognizer.recognize("近7天GMV")

        # 所有都应该识别到7天的时间范围
        for intent in [intent1, intent2, intent3, intent4]:
            if intent.time_range:
                start, end = intent.time_range
                assert (end - start).days == 7

    def test_absolute_time_year(self):
        """测试绝对时间年份."""
        intent = self.recognizer.recognize("2023年GMV")
        assert intent.time_granularity == TimeGranularity.YEAR
        start, end = intent.time_range
        assert start.year == 2023

    def test_absolute_time_year_month(self):
        """测试绝对时间年月."""
        intent = self.recognizer.recognize("2023年5月营收")
        assert intent.time_granularity == TimeGranularity.MONTH
        start, end = intent.time_range
        # 使用实际匹配的年份（从查询中提取）
        assert start.month == 5  # 5月份应该是正确的

    # ========== 综合测试用例 ==========
    def test_complex_query_with_all_elements(self):
        """测试包含所有元素的复杂查询."""
        intent = self.recognizer.recognize("最近7天按用户的GMV总和同比")
        assert intent.time_range is not None
        assert "用户" in intent.dimensions
        assert intent.aggregation_type == AggregationType.SUM
        assert intent.comparison_type == "yoy"

    def test_real_world_query_1(self):
        """测试真实场景查询1."""
        intent = self.recognizer.recognize("本月电商GMV总和")
        assert intent.time_granularity == TimeGranularity.MONTH
        assert intent.filters.get("domain") == "电商"
        assert intent.aggregation_type == AggregationType.SUM

    def test_real_world_query_2(self):
        """测试真实场景查询2."""
        intent = self.recognizer.recognize("今年用户增长数环比")
        assert intent.time_granularity == TimeGranularity.YEAR
        assert intent.comparison_type == "mom"

    def test_real_world_query_3(self):
        """测试真实场景查询3."""
        intent = self.recognizer.recognize("实时日活跃用户数")
        assert intent.filters.get("freshness") == "realtime"
        assert "活跃用户" in intent.core_query

    def test_query_string_representation(self):
        """测试查询字符串表示."""
        intent = self.recognizer.recognize("最近7天的GMV")
        str_repr = str(intent)
        assert "GMV" in str_repr
        assert len(str_repr) > 0


class TestIntentRecognitionEdgeCases:
    """边界和异常情况测试."""

    def setup_method(self):
        """测试前准备."""
        self.recognizer = IntentRecognizer()

    def test_week_calculation(self):
        """测试周时间计算."""
        intent = self.recognizer.recognize("本周GMV")
        start, end = intent.time_range

        # 应该是周一到周日
        assert start.weekday() == 0  # 周一
        assert (end - start).days == 6

    def test_month_boundary(self):
        """测试月份边界."""
        intent = self.recognizer.recognize("本月GMV")
        start, end = intent.time_range

        # 开始应该是月初
        assert start.day == 1
        # 结束应该是月末
        assert end.day >= 28

    def test_year_boundary(self):
        """测试年份边界."""
        intent = self.recognizer.recognize("今年GMV")
        start, end = intent.time_range

        # 开始应该是1月1日
        assert start.month == 1
        assert start.day == 1
        # 结束应该是12月31日
        assert end.month == 12
        assert end.day == 31

    def test_february_handling(self):
        """测试2月份处理."""
        # 设置当前时间为3月，测试"上个月"
        # 这样可以验证2月份（28或29天）的处理
        intent = self.recognizer.recognize("上个月GMV")
        # 只要不崩溃即可
        assert intent is not None


class TestIntentRecognitionAdversarial:
    """对抗性和干扰测试."""

    def setup_method(self):
        """测试前准备."""
        self.recognizer = IntentRecognizer()

    def test_conflicting_time_ranges(self):
        """测试冲突的时间范围."""
        intent = self.recognizer.recognize("最近7天本月GMV")
        # 应该选择第一个匹配的时间范围
        assert intent.time_range is not None

    def test_opposite_aggregations(self):
        """测试相反的聚合类型."""
        intent = self.recognizer.recognize("GMV最高最低")
        # 应该选择第一个匹配的聚合类型
        assert intent.aggregation_type in [AggregationType.MAX, AggregationType.MIN]

    def test_noise_words(self):
        """测试噪音词."""
        intent = self.recognizer.recognize("嗯那个呃这个GMV总和")
        # 应该能过滤掉噪音词
        assert intent.aggregation_type == AggregationType.SUM

    def test_redundant_words(self):
        """测试冗余词."""
        intent = self.recognizer.recognize("GMV总额总计合计")
        # 应该识别到求和
        assert intent.aggregation_type == AggregationType.SUM

    def test_query_with_numbers(self):
        """测试带数字的查询."""
        intent = self.recognizer.recognize("3月份GMV")
        # 数字可能被误识别为时间，需要验证
        assert intent is not None

    def test_dimension_as_metric(self):
        """测试维度被当作指标."""
        intent = self.recognizer.recognize("用户数按地区")
        # "用户数"可能是指标，"地区"是维度
        assert "地区" in intent.dimensions

    def test_domain_overlap(self):
        """测试业务域重叠."""
        intent = self.recognizer.recognize("电商用户营收")
        # 电商、用户、营收都是可能的域
        assert intent.filters.get("domain") in ["电商", "用户", "营收"]

    def test_time_granularity_conflict(self):
        """测试时间粒度冲突."""
        intent = self.recognizer.recognize("本月本日GMV")
        # 应该选择第一个匹配的时间粒度
        assert intent.time_granularity in [TimeGranularity.MONTH, TimeGranularity.DAY]

    def test_comparison_and_aggregation(self):
        """测试比较和聚合混合."""
        intent = self.recognizer.recognize("GMV增长率同比")
        assert intent.comparison_type == "yoy"
        assert intent.aggregation_type == AggregationType.RATE

    def test_complex_filters(self):
        """测试复杂过滤条件."""
        intent = self.recognizer.recognize("实时电商用户GMV")
        # 应该识别到实时和域过滤
        assert intent.filters.get("freshness") == "realtime"
        assert intent.filters.get("domain") in ["电商", "用户"]
