"""API 兼容性测试."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def mock_vector_store():
    """Mock 向量存储."""
    store = MagicMock()
    store.search.return_value = []
    return store


@pytest.fixture
def client_with_mock(mock_vector_store):
    """使用 mock 的测试客户端."""
    # Override app dependencies
    app.state.vector_store = mock_vector_store
    app.state.neo4j_client = None

    with TestClient(app) as client:
        yield client


class TestAPICompatibility:
    """API 兼容性测试."""

    # ========== 向后兼容性测试 ==========

    def test_old_client_without_conversation_id(self, client_with_mock):
        """测试旧客户端不传 conversation_id 仍能正常工作."""
        response = client_with_mock.post(
            "/api/v1/search",
            json={
                "query": "GMV",
                "top_k": 10,
                # 不传 conversation_id
            },
        )

        assert response.status_code == 200
        data = response.json()

        # 验证基本响应结构
        assert "query" in data
        assert "intent" in data
        assert "candidates" in data
        assert "total" in data
        assert "execution_time" in data

        # 验证新字段存在但为空（向后兼容）
        assert data["intent"]["trend_type"] is None
        assert data["intent"]["sort_requirement"] is None
        assert data["intent"]["threshold_filters"] == []

        # 验证会话ID已生成（新功能）
        assert data["conversation_id"] is not None
        assert isinstance(data["conversation_id"], str)

    def test_old_client_simple_query(self, client_with_mock):
        """测试旧客户端的简单查询."""
        response = client_with_mock.post(
            "/api/v1/search",
            json={
                "query": "查询营收",
                "top_k": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # 验证核心功能不受影响
        assert data["query"] == "查询营收"
        assert len(data["candidates"]) <= 5
        assert data["intent"]["core_query"] is not None

    # ========== 新功能测试 ==========

    def test_new_client_with_trend(self, client_with_mock):
        """测试新客户端识别趋势分析."""
        response = client_with_mock.post(
            "/api/v1/search",
            json={
                "query": "GMV上升趋势",
                "top_k": 10,
                "conversation_id": "test_conv_001",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # 验证趋势字段被识别
        assert data["intent"]["trend_type"] == "upward"
        assert data["conversation_id"] == "test_conv_001"

    def test_new_client_with_sort(self, client_with_mock):
        """测试新客户端识别排序需求."""
        response = client_with_mock.post(
            "/api/v1/search",
            json={
                "query": "GMV前10名",
                "top_k": 10,
                "conversation_id": "test_conv_002",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # 验证排序字段被识别
        assert data["intent"]["sort_requirement"] is not None
        assert data["intent"]["sort_requirement"]["top_n"] == 10
        assert data["intent"]["sort_requirement"]["order"] == "desc"

    def test_new_client_with_threshold(self, client_with_mock):
        """测试新客户端识别阈值过滤."""
        response = client_with_mock.post(
            "/api/v1/search",
            json={
                "query": "GMV大于100万",
                "top_k": 10,
                "conversation_id": "test_conv_003",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # 验证阈值字段被识别
        assert len(data["intent"]["threshold_filters"]) > 0
        f = data["intent"]["threshold_filters"][0]
        assert f["metric"] == "GMV"
        assert f["operator"] == ">"
        assert f["value"] == 100.0
        assert f["unit"] == "万"

    def test_new_client_with_complex_query(self, client_with_mock):
        """测试新客户端的复杂查询（组合多个意图）."""
        response = client_with_mock.post(
            "/api/v1/search",
            json={
                "query": "本月GMV上升趋势前10名",
                "top_k": 10,
                "conversation_id": "test_conv_004",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # 验证多个意图被识别
        assert data["intent"]["trend_type"] == "upward"
        assert data["intent"]["sort_requirement"] is not None
        assert data["intent"]["sort_requirement"]["top_n"] == 10
        assert data["intent"]["time_range"] is not None  # 本月

    # ========== 会话上下文测试 ==========

    def test_conversation_context_multi_turn(self, client_with_mock):
        """测试多轮对话的会话上下文."""
        conv_id = "test_conv_multi"

        # 第一轮：查询 GMV
        response1 = client_with_mock.post(
            "/api/v1/search",
            json={
                "query": "GMV",
                "top_k": 5,
                "conversation_id": conv_id,
            },
        )
        assert response1.status_code == 200

        # 第二轮：使用代词引用（"它的增长率" → "GMV的增长率"）
        # 注意：当前实现中，实体映射需要在会话中手动设置
        # 这里仅验证会话ID保持不变
        response2 = client_with_mock.post(
            "/api/v1/search",
            json={
                "query": "它的增长率",
                "top_k": 5,
                "conversation_id": conv_id,
            },
        )
        assert response2.status_code == 200
        assert response2.json()["conversation_id"] == conv_id

    def test_conversation_isolation(self, client_with_mock):
        """测试不同会话的隔离."""
        # 会话1
        response1 = client_with_mock.post(
            "/api/v1/search",
            json={
                "query": "GMV",
                "top_k": 5,
                "conversation_id": "conv_1",
            },
        )
        assert response1.status_code == 200

        # 会话2（应该不受会话1影响）
        response2 = client_with_mock.post(
            "/api/v1/search",
            json={
                "query": "DAU",
                "top_k": 5,
                "conversation_id": "conv_2",
            },
        )
        assert response2.status_code == 200

        # 验证会话ID不同
        assert response1.json()["conversation_id"] == "conv_1"
        assert response2.json()["conversation_id"] == "conv_2"

    def test_conversation_auto_generation(self, client_with_mock):
        """测试会话ID自动生成."""
        response = client_with_mock.post(
            "/api/v1/search",
            json={
                "query": "GMV",
                "top_k": 5,
                # 不传 conversation_id
            },
        )

        assert response.status_code == 200
        data = response.json()

        # 验证自动生成了会话ID
        assert data["conversation_id"] is not None
        assert len(data["conversation_id"]) > 0

    # ========== 边界情况测试 ==========

    def test_empty_query_should_fail(self, client_with_mock):
        """测试空查询应该失败."""
        response = client_with_mock.post(
            "/api/v1/search",
            json={
                "query": "",
                "top_k": 5,
            },
        )

        # 应该返回 422 验证错误
        assert response.status_code == 422

    def test_invalid_top_k_should_fail(self, client_with_mock):
        """测试无效的 top_k 应该失败."""
        response = client_with_mock.post(
            "/api/v1/search",
            json={
                "query": "GMV",
                "top_k": 999,  # 超过最大值 100
            },
        )

        # 应该返回 422 验证错误
        assert response.status_code == 422

    def test_score_threshold_validation(self, client_with_mock):
        """测试相似度阈值验证."""
        response = client_with_mock.post(
            "/api/v1/search",
            json={
                "query": "GMV",
                "top_k": 5,
                "score_threshold": 0.8,
            },
        )

        assert response.status_code == 200
