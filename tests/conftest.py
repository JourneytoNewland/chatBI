"""Pytest 共享配置和 fixtures."""

import pytest
from datetime import datetime

from src.inference.intent import IntentRecognizer


@pytest.fixture
def recognizer():
    """意图识别器实例.

    每个测试都会获得一个新的识别器实例，确保测试隔离。
    """
    return IntentRecognizer()


@pytest.fixture
def frozen_time():
    """冻结时间（用于时间相关测试）.

    Returns:
        datetime: 固定的测试时间 (2024-02-01 12:00:00)
    """
    return datetime(2024, 2, 1, 12, 0, 0)


# 趋势分析测试数据
@pytest.fixture
def trend_test_cases():
    """趋势分析测试用例数据.

    Returns:
        list[tuple[str, TrendType]]: (查询文本, 期望趋势类型)
    """
    from src.inference.intent import TrendType

    return [
        # 上升趋势
        ("GMV上升", TrendType.UPWARD),
        ("营收增长", TrendType.UPWARD),
        ("DAU提高", TrendType.UPWARD),
        ("销量增加", TrendType.UPWARD),
        # 下降趋势
        ("GMV下降", TrendType.DOWNWARD),
        ("营收下跌", TrendType.DOWNWARD),
        ("DAU减少", TrendType.DOWNWARD),
        ("销量降低", TrendType.DOWNWARD),
        # 波动
        ("GMV波动", TrendType.FLUCTUATING),
        ("DAU震荡", TrendType.FLUCTUATING),
        # 稳定
        ("销量稳定", TrendType.STABLE),
        ("营收持平", TrendType.STABLE),
    ]


# 排序需求测试数据
@pytest.fixture
def sort_test_cases():
    """排序需求测试用例数据.

    Returns:
        list[tuple[str, int, str]]: (查询文本, 期望top_n, 期望order)
    """
    from src.inference.intent import SortOrder

    return [
        ("GMV前10名", 10, SortOrder.DESC),
        ("Top5用户", 5, SortOrder.DESC),
        ("后5个地区", 5, SortOrder.ASC),
        ("Bottom 10", 10, SortOrder.ASC),
        ("最高GMV", None, SortOrder.DESC),
        ("最低DAU", None, SortOrder.ASC),
    ]


# 阈值过滤测试数据
@pytest.fixture
def threshold_test_cases():
    """阈值过滤测试用例数据.

    Returns:
        list[tuple[str, str, str, float, str]]: (查询, 期望指标, 期望运算符, 期望值, 期望单位)
    """
    return [
        ("GMV大于100万", "GMV", ">", 100.0, "万"),
        ("DAU<1000", "DAU", "<", 1000.0, None),
        ("营收>=500万", "营收", ">=", 500.0, "万"),
        ("GMV在100万到500万之间", "GMV", ">", 100.0, "万"),
    ]
