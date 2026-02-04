"""测试 MetricVectorizer 类."""

import numpy as np
import pytest

from src.recall.vector.models import MetricMetadata
from src.recall.vector.vectorizer import MetricVectorizer


class TestMetricVectorizer:
    """MetricVectorizer 测试套件."""

    @pytest.fixture
    def vectorizer(self) -> MetricVectorizer:
        """创建向量器实例."""
        return MetricVectorizer()

    @pytest.fixture
    def sample_metric(self) -> MetricMetadata:
        """创建示例指标数据."""
        return MetricMetadata(
            name="GMV",
            code="gmv",
            description="一定时期内成交总额",
            synonyms=["成交金额", "交易额", "总交易额"],
            domain="电商",
            formula="SUM(order_amount)",
        )

    def test_vectorize_output_shape(self, vectorizer: MetricVectorizer, sample_metric: MetricMetadata) -> None:
        """测试向量化输出维度正确."""
        embedding = vectorizer.vectorize(sample_metric)
        assert embedding.shape == (768,)
        assert isinstance(embedding, np.ndarray)

    def test_vectorize_normalized(self, vectorizer: MetricVectorizer, sample_metric: MetricMetadata) -> None:
        """测试向量已归一化."""
        embedding = vectorizer.vectorize(sample_metric)
        norm = np.linalg.norm(embedding)
        assert np.isclose(norm, 1.0, atol=1e-5)

    def test_vectorize_different_metrics(self, vectorizer: MetricVectorizer) -> None:
        """测试不同指标生成不同向量."""
        metric1 = MetricMetadata(
            name="GMV",
            code="gmv",
            description="成交总额",
            synonyms=["交易额"],
            domain="电商",
        )
        metric2 = MetricMetadata(
            name="DAU",
            code="dau",
            description="日活跃用户数",
            synonyms=["活跃用户"],
            domain="用户",
        )

        vec1 = vectorizer.vectorize(metric1)
        vec2 = vectorizer.vectorize(metric2)

        # 向量不应该完全相同
        assert not np.allclose(vec1, vec2)

    def test_vectorize_batch_empty_list(self, vectorizer: MetricVectorizer) -> None:
        """测试空列表批量向量化."""
        embeddings = vectorizer.vectorize_batch([])
        assert embeddings.shape == (0, 768)

    def test_vectorize_batch_shape(self, vectorizer: MetricVectorizer) -> None:
        """测试批量向量化输出维度."""
        metrics = [
            MetricMetadata(
                name=f"指标{i}",
                code=f"metric{i}",
                description=f"测试指标{i}",
                synonyms=[f"同义词{i}"],
                domain="测试",
            )
            for i in range(5)
        ]

        embeddings = vectorizer.vectorize_batch(metrics, show_progress=False)
        assert embeddings.shape == (5, 768)

    def test_vectorize_batch_consistency(self, vectorizer: MetricVectorizer, sample_metric: MetricMetadata) -> None:
        """测试批量向量化与单条向量化结果一致."""
        metrics = [sample_metric]
        batch_embeddings = vectorizer.vectorize_batch(metrics, show_progress=False)
        single_embedding = vectorizer.vectorize(sample_metric)

        np.testing.assert_array_almost_equal(batch_embeddings[0], single_embedding, decimal=5)

    def test_text_template_building(self, vectorizer: MetricVectorizer) -> None:
        """测试文本模板构建."""
        metric = MetricMetadata(
            name="GMV",
            code="gmv",
            description="成交总额",
            synonyms=["交易额", "成交金额"],
            domain="电商",
            formula="SUM(amount)",
        )

        template = vectorizer._build_text_template(metric)

        assert "指标名称: GMV" in template
        assert "指标编码: gmv" in template
        assert "业务含义: 成交总额" in template
        assert "同义词: 交易额、成交金额" in template
        assert "业务域: 电商" in template
        assert "计算公式: SUM(amount)" in template

    def test_text_template_with_empty_synonyms(self, vectorizer: MetricVectorizer) -> None:
        """测试空同义词列表的模板构建."""
        metric = MetricMetadata(
            name="GMV",
            code="gmv",
            description="成交总额",
            synonyms=[],
            domain="电商",
        )

        template = vectorizer._build_text_template(metric)
        assert "同义词: 无" in template

    def test_text_template_with_no_formula(self, vectorizer: MetricVectorizer) -> None:
        """测试无计算公式的模板构建."""
        metric = MetricMetadata(
            name="GMV",
            code="gmv",
            description="成交总额",
            synonyms=["交易额"],
            domain="电商",
            formula=None,
        )

        template = vectorizer._build_text_template(metric)
        assert "计算公式: 无" in template

    def test_embedding_dim_property(self, vectorizer: MetricVectorizer) -> None:
        """测试 embedding_dim 属性."""
        assert vectorizer.embedding_dim == 768

    def test_model_lazy_loading(self) -> None:
        """测试模型延迟加载."""
        vectorizer = MetricVectorizer()
        # 模型尚未加载
        assert vectorizer._model is None

        # 触发模型加载
        _ = vectorizer.embedding_dim
        # 模型已加载
        assert vectorizer._model is not None

    def test_similar_metrics_high_similarity(self, vectorizer: MetricVectorizer) -> None:
        """测试相似指标有较高的余弦相似度."""
        metric1 = MetricMetadata(
            name="GMV",
            code="gmv",
            description="成交总额",
            synonyms=["成交金额", "交易额"],
            domain="电商",
        )

        metric2 = MetricMetadata(
            name="成交总额",
            code="total_amount",
            description="GMV指标",
            synonyms=["GMV", "交易额"],
            domain="电商",
        )

        vec1 = vectorizer.vectorize(metric1)
        vec2 = vectorizer.vectorize(metric2)

        # 计算余弦相似度
        similarity = np.dot(vec1, vec2)
        # 相似指标应该有较高的相似度（>0.8）
        assert similarity > 0.8
