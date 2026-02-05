"""API 模型测试."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.api.models import IntentInfo, SearchRequest, SearchResponse


class TestAPIModels:
    """API 模型验证测试."""

    # ========== SearchRequest 测试 ==========

    def test_search_request_basic(self):
        """测试基本搜索请求."""
        req = SearchRequest(
            query="GMV",
            top_k=10,
        )
        assert req.query == "GMV"
        assert req.top_k == 10
        assert req.conversation_id is None  # 默认为 None

    def test_search_request_with_conversation_id(self):
        """测试带会话ID的搜索请求."""
        req = SearchRequest(
            query="GMV",
            top_k=10,
            conversation_id="test_conv_001",
        )
        assert req.conversation_id == "test_conv_001"

    def test_search_request_validation_empty_query(self):
        """测试空查询验证失败."""
        with pytest.raises(ValidationError):
            SearchRequest(
                query="",  # 空查询
                top_k=10,
            )

    def test_search_request_validation_invalid_top_k(self):
        """测试无效 top_k 验证失败."""
        with pytest.raises(ValidationError):
            SearchRequest(
                query="GMV",
                top_k=999,  # 超过最大值 100
            )

    def test_search_request_validation_invalid_score_threshold(self):
        """测试无效相似度阈值."""
        with pytest.raises(ValidationError):
            SearchRequest(
                query="GMV",
                top_k=10,
                score_threshold=1.5,  # 超过最大值 1.0
            )

    # ========== IntentInfo 测试 ==========

    def test_intent_info_basic(self):
        """测试基本意图信息."""
        intent = IntentInfo(
            core_query="GMV",
            time_granularity="day",
            aggregation_type="sum",
            dimensions=["地区", "产品"],
        )
        assert intent.core_query == "GMV"
        assert intent.time_granularity == "day"
        assert intent.aggregation_type == "sum"
        assert len(intent.dimensions) == 2

    def test_intent_info_with_new_fields(self):
        """测试带新字段的意图信息."""
        intent = IntentInfo(
            core_query="GMV",
            trend_type="upward",
            sort_requirement={"top_n": 10, "order": "desc", "metric": "GMV"},
            threshold_filters=[
                {"metric": "GMV", "operator": ">", "value": 100.0, "unit": "万"}
            ],
        )
        assert intent.trend_type == "upward"
        assert intent.sort_requirement["top_n"] == 10
        assert len(intent.threshold_filters) == 1

    def test_intent_info_default_new_fields(self):
        """测试新字段默认值."""
        intent = IntentInfo(
            core_query="GMV",
        )
        # 新字段应该有默认值
        assert intent.trend_type is None
        assert intent.sort_requirement is None
        assert intent.threshold_filters == []

    # ========== SearchResponse 测试 ==========

    def test_search_response_basic(self):
        """测试基本搜索响应."""
        response = SearchResponse(
            query="GMV",
            intent=None,
            candidates=[],
            total=0,
            execution_time=100.5,
        )
        assert response.query == "GMV"
        assert response.total == 0
        assert response.execution_time == 100.5
        assert response.conversation_id is None  # 默认为 None

    def test_search_response_with_conversation_id(self):
        """测试带会话ID的搜索响应."""
        response = SearchResponse(
            query="GMV",
            intent=None,
            candidates=[],
            total=0,
            execution_time=100.5,
            conversation_id="test_conv_001",
        )
        assert response.conversation_id == "test_conv_001"

    def test_search_response_with_intent(self):
        """测试带意图信息的搜索响应."""
        intent = IntentInfo(
            core_query="GMV",
            trend_type="upward",
            sort_requirement={"top_n": 10, "order": "desc"},
        )
        response = SearchResponse(
            query="GMV",
            intent=intent,
            candidates=[],
            total=0,
            execution_time=100.5,
        )
        assert response.intent.trend_type == "upward"
        assert response.intent.sort_requirement["top_n"] == 10

    # ========== 向后兼容性测试 ==========

    def test_backward_compatibility_old_request(self):
        """测试旧请求模型仍然有效."""
        # 旧代码只传基本字段
        req = SearchRequest(
            query="GMV",
            top_k=10,
            score_threshold=0.7,
        )
        # 新字段应该有默认值
        assert req.conversation_id is None

    def test_backward_compatibility_old_response(self):
        """测试旧响应模型仍然有效."""
        # 旧代码只创建基本字段
        intent = IntentInfo(
            core_query="GMV",
            time_range=None,
            time_granularity="day",
            aggregation_type=None,
            dimensions=[],
            comparison_type=None,
            filters={},
        )
        response = SearchResponse(
            query="GMV",
            intent=intent,
            candidates=[],
            total=0,
            execution_time=100.5,
        )
        # 新字段应该有默认值
        assert intent.trend_type is None
        assert intent.sort_requirement is None
        assert intent.threshold_filters == []
        assert response.conversation_id is None

    def test_new_fields_optional(self):
        """测试新字段都是可选的."""
        # 不传任何新字段
        intent = IntentInfo(core_query="GMV")
        assert intent.trend_type is None
        assert intent.sort_requirement is None
        assert intent.threshold_filters == []

        req = SearchRequest(query="GMV", top_k=10)
        assert req.conversation_id is None

        response = SearchResponse(
            query="GMV", intent=None, candidates=[], total=0, execution_time=100.5
        )
        assert response.conversation_id is None
