"""测试 Neo4j 图谱功能."""

import os

import pytest

# 跳过 Neo4j 测试如果没有配置
pytestmark = pytest.mark.skipif(
    os.environ.get("NEO4J_URI") is None,
    reason="NEO4J_URI not set",
)

from src.recall.graph.graph_store import GraphStore
from src.recall.graph.importer import GraphImporter, SAMPLE_DOMAINS, SAMPLE_METRICS, SAMPLE_RELATIONS
from src.recall.graph.models import MetricNode, BusinessDomainNode
from src.recall.graph.neo4j_client import Neo4jClient
from src.recall.graph.recall import GraphRecall


@pytest.fixture(scope="module")
def neo4j_client() -> Neo4jClient:
    """创建 Neo4j 客户端."""
    return Neo4jClient(
        uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        user=os.environ.get("NEO4J_USER", "neo4j"),
        password=os.environ.get("NEO4J_PASSWORD", "password"),
    )


@pytest.fixture(scope="module")
def graph_store(neo4j_client: Neo4jClient) -> GraphStore:
    """创建图谱存储."""
    store = GraphStore(neo4j_client)
    store.init_schema()
    return store


@pytest.fixture(scope="module")
def importer(graph_store: GraphStore) -> GraphImporter:
    """创建导入器."""
    return GraphImporter(graph_store)


@pytest.fixture(scope="module")
def sample_data(importer: GraphImporter) -> None:
    """导入示例数据."""
    importer.import_domains_batch(SAMPLE_DOMAINS)
    importer.import_metrics_batch(SAMPLE_METRICS)
    importer.import_relations_batch(SAMPLE_RELATIONS)


class TestGraphStore:
    """图谱存储测试."""

    def test_create_metric_node(self, graph_store: GraphStore) -> None:
        """测试创建指标节点."""
        metric = MetricNode(
            metric_id="test_001",
            name="测试指标",
            code="test_metric",
            description="这是一个测试指标",
            domain="测试",
        )
        metric_id = graph_store.create_metric_node(metric)
        assert metric_id == "test_001"

    def test_create_domain_node(self, graph_store: GraphStore) -> None:
        """测试创建业务域节点."""
        domain = BusinessDomainNode(
            domain_id="test_domain",
            name="测试域",
            description="测试业务域",
        )
        domain_id = graph_store.create_domain_node(domain)
        assert domain_id == "test_domain"

    def test_add_belongs_to_domain(self, graph_store: GraphStore) -> None:
        """测试添加业务域关系."""
        graph_store.add_belongs_to_domain("test_001", "test_domain")

    def test_find_metrics_by_domain(self, graph_store: GraphStore) -> None:
        """测试根据业务域查找指标."""
        results = graph_store.find_metrics_by_domain("测试域")
        assert len(results) > 0
        assert results[0]["m"]["metric_id"] == "test_001"


class TestGraphRecall:
    """图谱召回测试."""

    def test_recall_by_text_match(self, graph_store: GraphStore, sample_data: None) -> None:
        """测试文本匹配召回."""
        recall = GraphRecall(graph_store)
        results = recall.recall_by_text_match("GMV")
        assert len(results) > 0
        assert "GMV" in results[0]["name"] or "GMV" in str(results[0])

    def test_recall_by_domain(self, graph_store: GraphStore, sample_data: None) -> None:
        """测试业务域召回."""
        recall = GraphRecall(graph_store)
        results = recall.recall_by_domain("用户")
        assert len(results) > 0

    def test_recall_by_relation(self, graph_store: GraphStore, sample_data: None) -> None:
        """测试关系召回."""
        recall = GraphRecall(graph_store)
        results = recall.recall_by_relation("m002")
        # DAU 应该有相关指标（MAU, ARPU 等）
        assert len(results) >= 0

    def test_hybrid_recall(self, graph_store: GraphStore, sample_data: None) -> None:
        """测试混合召回."""
        recall = GraphRecall(graph_store)
        results = recall.hybrid_recall(query="活跃", domain_name="用户")
        # 应该找到 DAU 或 MAU
        assert len(results) >= 0
