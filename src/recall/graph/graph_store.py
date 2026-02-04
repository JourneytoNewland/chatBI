"""Neo4j 图谱存储管理."""

from typing import Any

from src.recall.graph.models import (
    BusinessDomainNode,
    DerivedFromRel,
    DimensionNode,
    MetricNode,
)
from src.recall.graph.neo4j_client import Neo4jClient


class GraphStore:
    """Neo4j 图谱存储管理器.

    提供图谱数据的创建、导入和查询功能。
    """

    # Cypher 约束和索引定义
    CONSTRAINTS = [
        "CREATE CONSTRAINT metric_id_unique IF NOT EXISTS FOR (m:Metric) REQUIRE m.metric_id IS UNIQUE",
        "CREATE CONSTRAINT dimension_id_unique IF NOT EXISTS FOR (d:Dimension) REQUIRE d.dimension_id IS UNIQUE",
        "CREATE CONSTRAINT domain_id_unique IF NOT EXISTS FOR (bd:BusinessDomain) REQUIRE bd.domain_id IS UNIQUE",
        "CREATE INDEX metric_name_index IF NOT EXISTS FOR (m:Metric) ON (m.name)",
        "CREATE INDEX metric_code_index IF NOT EXISTS FOR (m:Metric) ON (m.code)",
        "CREATE INDEX metric_domain_index IF NOT EXISTS FOR (m:Metric) ON (m.domain)",
    ]

    def __init__(self, client: Neo4jClient) -> None:
        """初始化图谱存储.

        Args:
            client: Neo4j 客户端实例
        """
        self.client = client

    def init_schema(self) -> None:
        """初始化图谱结构（创建约束和索引）."""
        for constraint in self.CONSTRAINTS:
            try:
                self.client.execute_write(constraint)
            except Exception as e:
                print(f"Warning: Failed to create constraint: {e}")

    def create_metric_node(self, metric: MetricNode) -> str:
        """创建指标节点.

        Args:
            metric: 指标节点数据

        Returns:
            创建的节点 ID
        """
        query = """
        MERGE (m:Metric {metric_id: $metric_id})
        SET m.name = $name,
            m.code = $code,
            m.description = $description,
            m.domain = $domain,
            m.importance = $importance,
            m.synonyms = $synonyms,
            m.formula = $formula
        RETURN m.metric_id as metric_id
        """

        params = metric.to_cypher_props()
        result = self.client.execute_query(query, params)
        return result[0]["metric_id"]

    def create_dimension_node(self, dimension: DimensionNode) -> str:
        """创建维度节点.

        Args:
            dimension: 维度节点数据

        Returns:
            创建的节点 ID
        """
        query = """
        MERGE (d:Dimension {dimension_id: $dimension_id})
        SET d.name = $name,
            d.description = $description,
            d.values = $values
        RETURN d.dimension_id as dimension_id
        """

        params = dimension.to_cypher_props()
        result = self.client.execute_query(query, params)
        return result[0]["dimension_id"]

    def create_domain_node(self, domain: BusinessDomainNode) -> str:
        """创建业务域节点.

        Args:
            domain: 业务域节点数据

        Returns:
            创建的节点 ID
        """
        query = """
        MERGE (bd:BusinessDomain {domain_id: $domain_id})
        SET bd.name = $name,
            bd.description = $description
        RETURN bd.domain_id as domain_id
        """

        params = domain.to_cypher_props()
        result = self.client.execute_query(query, params)
        return result[0]["domain_id"]

    def add_belongs_to_domain(
        self,
        metric_id: str,
        domain_id: str,
        weight: float = 1.0,
    ) -> None:
        """添加指标-业务域关系.

        Args:
            metric_id: 指标 ID
            domain_id: 业务域 ID
            weight: 关系权重
        """
        query = """
        MATCH (m:Metric {metric_id: $metric_id})
        MATCH (bd:BusinessDomain {domain_id: $domain_id})
        MERGE (m)-[r:BELONGS_TO_DOMAIN]->(bd)
        SET r.weight = $weight
        """

        self.client.execute_write(
            query,
            {"metric_id": metric_id, "domain_id": domain_id, "weight": weight},
        )

    def add_has_dimension(
        self,
        metric_id: str,
        dimension_id: str,
        required: bool = True,
    ) -> None:
        """添加指标-维度关系.

        Args:
            metric_id: 指标 ID
            dimension_id: 维度 ID
            required: 是否必需维度
        """
        query = """
        MATCH (m:Metric {metric_id: $metric_id})
        MATCH (d:Dimension {dimension_id: $dimension_id})
        MERGE (m)-[r:HAS_DIMENSION]->(d)
        SET r.required = $required
        """

        self.client.execute_write(
            query,
            {"metric_id": metric_id, "dimension_id": dimension_id, "required": required},
        )

    def add_derived_from(
        self,
        source_metric_id: str,
        target_metric_id: str,
        confidence: float = 0.8,
        formula: str | None = None,
    ) -> None:
        """添加指标派生关系.

        Args:
            source_metric_id: 源指标 ID（派生指标）
            target_metric_id: 目标指标 ID（基础指标）
            confidence: 置信度
            formula: 派生公式
        """
        query = """
        MATCH (source:Metric {metric_id: $source_metric_id})
        MATCH (target:Metric {metric_id: $target_metric_id})
        MERGE (source)-[r:DERIVED_FROM]->(target)
        SET r.confidence = $confidence,
            r.formula = $formula
        """

        self.client.execute_write(
            query,
            {
                "source_metric_id": source_metric_id,
                "target_metric_id": target_metric_id,
                "confidence": confidence,
                "formula": formula,
            },
        )

    def add_correlates_with(
        self,
        metric_id_1: str,
        metric_id_2: str,
        weight: float = 0.5,
        correlation_type: str = "positive",
    ) -> None:
        """添加指标相关性关系.

        Args:
            metric_id_1: 指标 1 ID
            metric_id_2: 指标 2 ID
            weight: 相关权重
            correlation_type: 相关类型（positive/negative）
        """
        query = """
        MATCH (m1:Metric {metric_id: $metric_id_1})
        MATCH (m2:Metric {metric_id: $metric_id_2})
        MERGE (m1)-[r:CORRELATES_WITH]->(m2)
        SET r.weight = $weight,
            r.correlation_type = $correlation_type
        """

        self.client.execute_write(
            query,
            {
                "metric_id_1": metric_id_1,
                "metric_id_2": metric_id_2,
                "weight": weight,
                "correlation_type": correlation_type,
            },
        )

    def find_metrics_by_domain(self, domain_name: str) -> list[dict[str, Any]]:
        """根据业务域查找指标.

        Args:
            domain_name: 业务域名称

        Returns:
            指标列表
        """
        query = """
        MATCH (m:Metric)-[:BELONGS_TO_DOMAIN]->(bd:BusinessDomain {name: $domain_name})
        RETURN m
        ORDER BY m.importance DESC
        """

        return self.client.execute_query(query, {"domain_name": domain_name})

    def find_related_metrics(
        self,
        metric_id: str,
        relation_types: list[str] | None = None,
        max_depth: int = 2,
    ) -> list[dict[str, Any]]:
        """查找相关指标（基于关系路径）.

        Args:
            metric_id: 起始指标 ID
            relation_types: 关系类型过滤（可选）
            max_depth: 最大路径深度

        Returns:
            相关指标列表
        """
        if relation_types:
            rel_pattern = "|".join(relation_types)
            query = f"""
            MATCH (m:Metric {{metric_id: $metric_id}})-[:{rel_pattern}*1..{max_depth}]-(related:Metric)
            WHERE related.metric_id <> $metric_id
            RETURN DISTINCT related.metric_id as metric_id,
                           related.name as name,
                           related.code as code,
                           related.description as description
            """
        else:
            query = f"""
            MATCH (m:Metric {{metric_id: $metric_id}})-[*1..{max_depth}]-(related:Metric)
            WHERE related.metric_id <> $metric_id
            RETURN DISTINCT related.metric_id as metric_id,
                           related.name as name,
                           related.code as code,
                           related.description as description
            """

        return self.client.execute_query(query, {"metric_id": metric_id})

    def find_metrics_by_name_or_synonym(self, text: str) -> list[dict[str, Any]]:
        """根据名称或同义词查找指标.

        Args:
            text: 查询文本

        Returns:
            匹配的指标列表
        """
        query = """
        MATCH (m:Metric)
        WHERE m.name CONTAINS $text
           OR $text IN m.synonyms
           OR m.code CONTAINS $text
        RETURN m.metric_id as metric_id,
               m.name as name,
               m.code as code,
               m.description as description,
               m.domain as domain
        ORDER BY m.importance DESC
        """

        return self.client.execute_query(query, {"text": text})

    def get_metric_details(self, metric_id: str) -> dict[str, Any] | None:
        """获取指标详细信息（包括所有关系）.

        Args:
            metric_id: 指标 ID

        Returns:
            指标详情字典
        """
        query = """
        MATCH (m:Metric {metric_id: $metric_id})
        OPTIONAL MATCH (m)-[:BELONGS_TO_DOMAIN]->(bd:BusinessDomain)
        OPTIONAL MATCH (m)-[:HAS_DIMENSION]->(d:Dimension)
        OPTIONAL MATCH (m)-[:DERIVED_FROM]->(base:Metric)
        OPTIONAL MATCH (m)-[:CORRELATES_WITH]-(corr:Metric)
        RETURN m,
               bd,
               collect(DISTINCT d) as dimensions,
               collect(DISTINCT base) as derived_from,
               collect(DISTINCT corr) as correlates_with
        """

        result = self.client.execute_query(query, {"metric_id": metric_id})
        return result[0] if result else None
