"""测试 QdrantVectorStore 类."""

import numpy as np
import pytest
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from src.config import QdrantConfig
from src.recall.vector.qdrant_store import QdrantVectorStore


class TestQdrantVectorStore:
    """QdrantVectorStore 测试套件."""

    @pytest.fixture
    def in_memory_qdrant(self) -> QdrantClient:
        """创建内存模式 Qdrant 客户端."""
        return QdrantClient(":memory:")

    @pytest.fixture
    def vector_store(self, in_memory_qdrant: QdrantClient) -> QdrantVectorStore:
        """创建向量存储实例（使用内存模式）."""
        # 创建临时 collection
        in_memory_qdrant.create_collection(
            collection_name="test_metrics",
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )

        # 创建配置
        config = QdrantConfig(collection_name="test_metrics")

        # 创建 store 并替换为 in-memory 客户端
        store = QdrantVectorStore(config=config)
        store.client = in_memory_qdrant

        return store

    @pytest.fixture
    def sample_vectors(self) -> list[np.ndarray]:
        """创建示例向量."""
        np.random.seed(42)
        return [np.random.randn(768) for _ in range(10)]

    @pytest.fixture
    def sample_payloads(self) -> list[dict]:
        """创建示例 payload."""
        return [
            {
                "metric_id": f"metric_{i}",
                "name": f"指标{i}",
                "code": f"metric_{i}",
                "description": f"测试指标{i}的描述",
                "domain": "测试域",
            }
            for i in range(10)
        ]

    def test_create_collection(self, vector_store: QdrantVectorStore) -> None:
        """测试创建 collection."""
        # Collection 在 fixture 中已经创建
        assert vector_store.collection_exists() is True

    def test_upsert_vectors(
        self,
        vector_store: QdrantVectorStore,
        sample_vectors: list[np.ndarray],
        sample_payloads: list[dict],
    ) -> None:
        """测试批量 upsert."""
        ids = [f"metric_{i}" for i in range(10)]
        count = vector_store.upsert(ids, sample_vectors, sample_payloads)

        assert count == 10
        assert vector_store.count() == 10

    def test_upsert_empty_list(self, vector_store: QdrantVectorStore) -> None:
        """测试空列表 upsert."""
        count = vector_store.upsert([], [], [])
        assert count == 0

    def test_upsert_length_mismatch(
        self,
        vector_store: QdrantVectorStore,
        sample_vectors: list[np.ndarray],
        sample_payloads: list[dict],
    ) -> None:
        """测试长度不匹配的情况."""
        ids = ["metric_1", "metric_2"]

        with pytest.raises(ValueError, match="Length mismatch"):
            vector_store.upsert(ids, sample_vectors, sample_payloads)

    def test_search(
        self,
        vector_store: QdrantVectorStore,
        sample_vectors: list[np.ndarray],
        sample_payloads: list[dict],
    ) -> None:
        """测试 ANN 检索."""
        # 先插入数据
        ids = [f"metric_{i}" for i in range(10)]
        vector_store.upsert(ids, sample_vectors, sample_payloads)

        # 使用第一个向量作为查询
        query_vector = sample_vectors[0]
        results = vector_store.search(query_vector, top_k=5)

        assert len(results) == 5
        # 第一个结果应该是自己，分数应该最高
        assert results[0]["id"] == "metric_0"
        assert results[0]["score"] > 0.99  # 自己应该非常相似

    def test_search_with_threshold(
        self,
        vector_store: QdrantVectorStore,
        sample_vectors: list[np.ndarray],
        sample_payloads: list[dict],
    ) -> None:
        """测试带阈值的检索."""
        ids = [f"metric_{i}" for i in range(10)]
        vector_store.upsert(ids, sample_vectors, sample_payloads)

        query_vector = sample_vectors[0]
        results = vector_store.search(query_vector, top_k=10, score_threshold=0.9)

        # 应该只有自己分数 > 0.9
        assert len(results) >= 1
        assert all(r["score"] >= 0.9 for r in results)

    def test_count(
        self,
        vector_store: QdrantVectorStore,
        sample_vectors: list[np.ndarray],
        sample_payloads: list[dict],
    ) -> None:
        """测试计数."""
        assert vector_store.count() == 0

        ids = [f"metric_{i}" for i in range(5)]
        vector_store.upsert(ids, sample_vectors[:5], sample_payloads[:5])

        assert vector_store.count() == 5

    def test_delete_collection(self, vector_store: QdrantVectorStore) -> None:
        """测试删除 collection."""
        assert vector_store.collection_exists() is True
        vector_store.delete_collection()
        assert vector_store.collection_exists() is False

    def test_vector_and_numpy_array_conversion(
        self,
        vector_store: QdrantVectorStore,
        sample_vectors: list[np.ndarray],
        sample_payloads: list[dict],
    ) -> None:
        """测试 numpy 数组和列表的转换."""
        ids = [f"metric_{i}" for i in range(3)]

        # 混合使用 numpy 数组和列表
        vectors_mixed = [
            sample_vectors[0],
            sample_vectors[1].tolist(),
            sample_vectors[2],
        ]

        count = vector_store.upsert(ids, vectors_mixed, sample_payloads[:3])
        assert count == 3

    def test_batch_upsert(
        self,
        vector_store: QdrantVectorStore,
        sample_vectors: list[np.ndarray],
        sample_payloads: list[dict],
    ) -> None:
        """测试批量 upsert（小批次大小）."""
        ids = [f"metric_{i}" for i in range(10)]

        # 使用小批次大小
        count = vector_store.upsert(
            ids,
            sample_vectors,
            sample_payloads,
            batch_size=3,
        )

        assert count == 10

    def test_search_result_structure(
        self,
        vector_store: QdrantVectorStore,
        sample_vectors: list[np.ndarray],
        sample_payloads: list[dict],
    ) -> None:
        """测试检索结果的结构."""
        ids = [f"metric_{i}" for i in range(5)]
        vector_store.upsert(ids, sample_vectors[:5], sample_payloads[:5])

        results = vector_store.search(sample_vectors[0], top_k=3)

        for result in results:
            assert "id" in result
            assert "score" in result
            assert "payload" in result
            assert isinstance(result["score"], float)
            assert 0 <= result["score"] <= 1
            assert isinstance(result["payload"], dict)
