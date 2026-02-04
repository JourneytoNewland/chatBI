"""测试检索 API."""

import time
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from src.api.main import app
from src.config import QdrantConfig
from src.recall.vector.qdrant_store import QdrantVectorStore


@pytest.fixture
def test_store() -> QdrantVectorStore:
    """创建测试用的向量存储."""
    # 使用内存模式
    client = QdrantClient(":memory:")

    # 创建 collection
    client.create_collection(
        collection_name="test_metrics",
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )

    # 插入测试数据
    test_data = [
        {
            "id": "m001",
            "vector": np.random.randn(768).tolist(),
            "payload": {
                "metric_id": "m001",
                "name": "GMV",
                "code": "gmv",
                "description": "成交总额",
                "domain": "电商",
                "synonyms": ["成交金额", "交易额"],
                "formula": "SUM(order_amount)",
            },
        },
        {
            "id": "m002",
            "vector": np.random.randn(768).tolist(),
            "payload": {
                "metric_id": "m002",
                "name": "DAU",
                "code": "dau",
                "description": "日活跃用户数",
                "domain": "用户",
                "synonyms": ["日活", "活跃用户"],
                "formula": "COUNT(DISTINCT user_id)",
            },
        },
        {
            "id": "m003",
            "vector": np.random.randn(768).tolist(),
            "payload": {
                "metric_id": "m003",
                "name": "MAU",
                "code": "mau",
                "description": "月活跃用户数",
                "domain": "用户",
                "synonyms": ["月活"],
                "formula": "COUNT(DISTINCT user_id) WHERE date >= TODAY - 30",
            },
        },
    ]

    # Upsert 数据
    points = [
        {
            "id": d["id"],
            "vector": d["vector"],
            "payload": d["payload"],
        }
        for d in test_data
    ]
    client.upsert(collection_name="test_metrics", points=points)

    # 创建 store 并注入客户端
    config = QdrantConfig(collection_name="test_metrics")
    store = QdrantVectorStore(config=config)
    store.client = client

    return store


class TestSearchAPI:
    """检索 API 测试套件."""

    @pytest.fixture
    def client(self, test_store: QdrantVectorStore) -> TestClient:
        """创建测试客户端."""
        # 注入 test_store 到应用状态
        app.state.vector_store = test_store
        return TestClient(app)

    def test_health_check(self, client: TestClient) -> None:
        """测试健康检查接口."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data

    def test_search_exact_match(self, client: TestClient) -> None:
        """测试精确匹配查询."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "GMV",
                "top_k": 3,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "GMV"
        assert len(data["candidates"]) <= 3
        assert data["total"] == len(data["candidates"])
        assert "execution_time" in data
        assert all(c["score"] > 0 for c in data["candidates"])

    def test_search_synonym(self, client: TestClient) -> None:
        """测试同义词查询."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "成交总额",
                "top_k": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        # 查询"成交总额"应该返回 GMV 在结果中
        top_names = [c["name"] for c in data["candidates"]]
        assert "GMV" in top_names

    def test_search_empty_query(self, client: TestClient) -> None:
        """测试空查询."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "",
                "top_k": 10,
            },
        )

        # 应该返回 422 验证错误
        assert response.status_code == 422

    def test_search_invalid_top_k(self, client: TestClient) -> None:
        """测试无效的 top_k 值."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "GMV",
                "top_k": 200,  # 超过最大值 100
            },
        )

        # 应该返回 422 验证错误
        assert response.status_code == 422

    def test_search_response_format(self, client: TestClient) -> None:
        """测试响应格式."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "测试查询",
                "top_k": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # 验证必需字段
        assert "query" in data
        assert "candidates" in data
        assert "total" in data
        assert "execution_time" in data

        # 验证 candidates 格式
        if data["candidates"]:
            candidate = data["candidates"][0]
            assert "metric_id" in candidate
            assert "name" in candidate
            assert "code" in candidate
            assert "description" in candidate
            assert "domain" in candidate
            assert "score" in candidate
            assert isinstance(candidate["score"], float)
            assert 0 <= candidate["score"] <= 1

    def test_search_with_score_threshold(self, client: TestClient) -> None:
        """测试带相似度阈值的查询."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "测试",
                "top_k": 10,
                "score_threshold": 0.8,
            },
        )

        assert response.status_code == 200
        data = response.json()
        # 所有结果分数应该 >= 0.8
        assert all(c["score"] >= 0.8 for c in data["candidates"])

    def test_search_execution_time(self, client: TestClient) -> None:
        """测试执行时间记录."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "GMV",
                "top_k": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["execution_time"] >= 0
        # 应该在合理时间内完成（< 5秒）
        assert data["execution_time"] < 5000
