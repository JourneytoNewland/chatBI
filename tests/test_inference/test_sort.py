"""排序需求识别测试."""

import pytest
from src.inference.intent import SortOrder


class TestSortRequirement:
    """排序需求测试."""

    def setup_method(self):
        """测试前准备."""
        from src.inference.intent import IntentRecognizer

        self.recognizer = IntentRecognizer()

    # ========== 正常用例（7个）==========

    def test_sort_top_n_explicit(self):
        """测试明确Top N."""
        intent = self.recognizer.recognize("GMV前10名")
        assert intent.sort_requirement is not None
        assert intent.sort_requirement.top_n == 10
        assert intent.sort_requirement.order == SortOrder.DESC

    def test_sort_top_n_with_english(self):
        """测试英文Top N."""
        intent = self.recognizer.recognize("Top5用户")
        assert intent.sort_requirement is not None
        assert intent.sort_requirement.top_n == 5
        assert intent.sort_requirement.order == SortOrder.DESC

    def test_sort_bottom_n(self):
        """测试Bottom N."""
        intent = self.recognizer.recognize("后5个地区")
        assert intent.sort_requirement is not None
        assert intent.sort_requirement.top_n == 5
        assert intent.sort_requirement.order == SortOrder.ASC

    def test_sort_highest(self):
        """测试最高表达."""
        intent = self.recognizer.recognize("最高GMV")
        assert intent.sort_requirement is not None
        assert intent.sort_requirement.order == SortOrder.DESC
        assert intent.sort_requirement.top_n is None  # "最高"没有数字

    def test_sort_lowest(self):
        """测试最低表达."""
        intent = self.recognizer.recognize("最低DAU")
        assert intent.sort_requirement is not None
        assert intent.sort_requirement.order == SortOrder.ASC
        assert intent.sort_requirement.top_n is None

    def test_sort_with_time_range(self):
        """测试排序+时间范围."""
        intent = self.recognizer.recognize("本月GMV前10")
        assert intent.sort_requirement is not None
        assert intent.sort_requirement.top_n == 10
        assert intent.time_range is not None

    def test_sort_with_aggregation(self):
        """测试排序+聚合."""
        intent = self.recognizer.recognize("平均销售额最高的5个产品")
        assert intent.sort_requirement is not None
        assert intent.sort_requirement.top_n == 5
        assert intent.aggregation_type.value == "avg"

    # ========== 边界用例（3个）==========

    def test_sort_no_number(self):
        """测试无数字排序."""
        intent = self.recognizer.recognize("GMV前几个")
        # 无数字，top_n为None
        assert intent.sort_requirement is not None
        assert intent.sort_requirement.top_n is None

    def test_sort_invalid_number(self):
        """测试无效数字."""
        intent = self.recognizer.recognize("GMV前0个")
        # 0也是有效数字，虽然无意义
        if intent.sort_requirement:
            assert intent.sort_requirement.top_n == 0

    def test_sort_very_large_number(self):
        """测试超大数字."""
        intent = self.recognizer.recognize("GMV前999999个")
        # 超大数字，保留原值
        assert intent.sort_requirement is not None
        assert intent.sort_requirement.top_n == 999999

    # ========== 对抗用例（2个）==========

    def test_sort_multiple_requirements(self):
        """测试多个排序需求."""
        intent = self.recognizer.recognize("GMV前10个 DAU前5个")
        # 应该识别到第一个
        assert intent.sort_requirement is not None
        assert intent.sort_requirement.top_n == 10

    def test_sort_conflicting(self):
        """测试冲突排序."""
        intent = self.recognizer.recognize("GMV前10个后5个")
        # 应该识别到第一个
        assert intent.sort_requirement is not None
        assert intent.sort_requirement.order == SortOrder.DESC
