"""端到端集成测试.

测试完整的向量化 -> 存储 -> 检索流程.
"""

import numpy as np
import pytest
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from src.config import QdrantConfig
from src.recall.vector.models import MetricMetadata
from src.recall.vector.qdrant_store import QdrantVectorStore
from src.recall.vector.vectorizer import MetricVectorizer


class TestEndToEndIntegration:
    """端到端集成测试."""

    @pytest.fixture
    def vectorizer(self) -> MetricVectorizer:
        """创建向量化器."""
        return MetricVectorizer()

    @pytest.fixture
    def vector_store(self) -> QdrantVectorStore:
        """创建向量存储."""
        client = QdrantClient(":memory:")
        client.create_collection(
            collection_name="test_integration",
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )

        config = QdrantConfig(collection_name="test_integration")
        store = QdrantVectorStore(config=config)
        store.client = client

        return store

    @pytest.fixture
    def sample_metrics(self) -> list[MetricMetadata]:
        """创建示例指标."""
        return [
            MetricMetadata(
                name="GMV",
                code="gmv",
                description="成交总额",
                synonyms=["成交金额", "交易额"],
                domain="电商",
                formula="SUM(order_amount)",
            ),
            MetricMetadata(
                name="DAU",
                code="dau",
                description="日活跃用户数",
                synonyms=["日活"],
                domain="用户",
                formula="COUNT(DISTINCT user_id)",
            ),
            MetricMetadata(
                name="转化率",
                code="conversion_rate",
                description="访客转化为付费用户的比例",
                synonyms=["付费转化率"],
                domain="增长",
                formula="paid_users / total_visitors * 100%",
            ),
        ]

    def test_full_pipeline(
        self,
        vectorizer: MetricVectorizer,
        vector_store: QdrantVectorStore,
        sample_metrics: list[MetricMetadata],
    ) -> None:
        """测试完整的向量化 -> 存储 -> 检索流程."""
        # 1. 向量化
        embeddings = vectorizer.vectorize_batch(sample_metrics, show_progress=False)
        assert embeddings.shape == (3, 768)

        # 2. 存储
        metric_ids = [f"m{i:03d}" for i in range(3)]
        payloads = [
            {
                "metric_id": mid,
                "name": m.name,
                "code": m.code,
                "description": m.description,
                "synonyms": m.synonyms,
                "domain": m.domain,
                "formula": m.formula,
            }
            for mid, m in zip(metric_ids, sample_metrics)
        ]

        count = vector_store.upsert(metric_ids, embeddings, payloads)
        assert count == 3
        assert vector_store.count() == 3

        # 3. 检索 - 精确匹配
        query = "GMV"
        query_metadata = MetricMetadata(
            name=query,
            code=query,
            description=query,
            synonyms=[],
            domain="查询",
        )
        query_vector = vectorizer.vectorize(query_metadata)

        results = vector_store.search(query_vector, top_k=3)

        # 验证结果
        assert len(results) <= 3
        assert results[0]["payload"]["name"] == "GMV"
        assert results[0]["score"] > 0.9  # 自己应该非常相似

        # 4. 检索 - 同义词
        query_synonym = "成交金额"
        query_metadata_synonym = MetricMetadata(
            name=query_synonym,
            code=query_synonym,
            description=query_synonym,
            synonyms=[],
            domain="查询",
        )
        query_vector_synonym = vectorizer.vectorize(query_metadata_synonym)

        results_synonym = vector_store.search(query_vector_synonym, top_k=3)

        # 同义词应该也能找到 GMV
        found_gmv = any(r["payload"]["name"] == "GMV" for r in results_synonym)
        assert found_gmv, "同义词查询应该能找到对应的指标"

    def test_batch_upsert_large_dataset(
        self,
        vectorizer: MetricVectorizer,
        vector_store: QdrantVectorStore,
    ) -> None:
        """测试批量插入大量数据."""
        # 创建 100 个测试指标
        n_metrics = 100
        metrics = [
            MetricMetadata(
                name=f"指标{i}",
                code=f"metric_{i}",
                description=f"测试指标{i}的描述",
                synonyms=[f"同义词{i}"],
                domain="测试",
            )
            for i in range(n_metrics)
        ]

        # 批量向量化
        embeddings = vectorizer.vectorize_batch(metrics, show_progress=False)
        assert embeddings.shape == (n_metrics, 768)

        # 批量存储
        metric_ids = [f"m{i:04d}" for i in range(n_metrics)]
        payloads = [
            {
                "metric_id": mid,
                "name": m.name,
                "code": m.code,
                "description": m.description,
                "synonyms": m.synonyms,
                "domain": m.domain,
            }
            for mid, m in zip(metric_ids, metrics)
        ]

        count = vector_store.upsert(metric_ids, embeddings, payloads, batch_size=32)
        assert count == n_metrics
        assert vector_store.count() == n_metrics

    def test_retrieve_top_k_variations(
        self,
        vectorizer: MetricVectorizer,
        vector_store: QdrantVectorStore,
        sample_metrics: list[MetricMetadata],
    ) -> None:
        """测试不同的 top_k 值."""
        # 先插入数据
        embeddings = vectorizer.vectorize_batch(sample_metrics, show_progress=False)
        metric_ids = [f"m{i:03d}" for i in range(len(sample_metrics))]
        payloads = [
            {
                "metric_id": mid,
                "name": m.name,
                "code": m.code,
                "description": m.description,
                "domain": m.domain,
            }
            for mid, m in zip(metric_ids, sample_metrics)
        ]

        vector_store.upsert(metric_ids, embeddings, payloads)

        # 测试不同的 top_k
        query_metadata = MetricMetadata(
            name="GMV",
            code="gmv",
            description="成交总额",
            synonyms=[],
            domain="查询",
        )
        query_vector = vectorizer.vectorize(query_metadata)

        for top_k in [1, 2, 5, 10]:
            results = vector_store.search(query_vector, top_k=top_k)
            assert len(results) <= top_k

    def test_search_with_threshold_filters(
        self,
        vectorizer: MetricVectorizer,
        vector_store: QdrantVectorStore,
        sample_metrics: list[MetricMetadata],
    ) -> None:
        """测试相似度阈值过滤."""
        # 插入数据
        embeddings = vectorizer.vectorize_batch(sample_metrics, show_progress=False)
        metric_ids = [f"m{i:03d}" for i in range(len(sample_metrics))]
        payloads = [
            {
                "metric_id": mid,
                "name": m.name,
                "code": m.code,
                "description": m.description,
                "domain": m.domain,
            }
            for mid, m in zip(metric_ids, sample_metrics)
        ]

        vector_store.upsert(metric_ids, embeddings, payloads)

        # 查询
        query_metadata = MetricMetadata(
            name="GMV",
            code="gmv",
            description="成交总额",
            synonyms=[],
            domain="查询",
        )
        query_vector = vectorizer.vectorize(query_metadata)

        # 设置高阈值
        results_high = vector_store.search(query_vector, top_k=10, score_threshold=0.95)
        for result in results_high:
            assert result["score"] >= 0.95

        # 设置低阈值
        results_low = vector_store.search(query_vector, top_k=10, score_threshold=0.5)
        # 低阈值应该返回更多或相等的结果
        assert len(results_low) >= len(results_high)
