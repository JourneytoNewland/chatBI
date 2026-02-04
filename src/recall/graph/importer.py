"""图谱批量导入工具."""

from typing import Any

from src.recall.graph.graph_store import GraphStore
from src.recall.graph.models import (
    BusinessDomainNode,
    DerivedFromRel,
    DimensionNode,
    MetricNode,
)
from src.recall.graph.neo4j_client import Neo4jClient


class GraphImporter:
    """图谱数据批量导入工具."""

    def __init__(self, graph_store: GraphStore) -> None:
        """初始化导入器.

        Args:
            graph_store: 图谱存储实例
        """
        self.store = graph_store

    def import_metrics_batch(
        self,
        metrics: list[dict[str, Any]],
        show_progress: bool = True,
    ) -> int:
        """批量导入指标节点.

        Args:
            metrics: 指标数据列表
            show_progress: 是否显示进度

        Returns:
            成功导入的数量
        """
        count = 0
        total = len(metrics)

        for i, metric_data in enumerate(metrics):
            try:
                metric = MetricNode(
                    metric_id=metric_data["metric_id"],
                    name=metric_data["name"],
                    code=metric_data["code"],
                    description=metric_data["description"],
                    domain=metric_data["domain"],
                    importance=metric_data.get("importance", 0.5),
                    synonyms=metric_data.get("synonyms", []),
                    formula=metric_data.get("formula"),
                )

                self.store.create_metric_node(metric)
                count += 1

                if show_progress and (i + 1) % 10 == 0:
                    print(f"  进度: {i + 1}/{total}")

            except Exception as e:
                print(f"  警告: 导入指标 {metric_data.get('metric_id')} 失败: {e}")

        return count

    def import_dimensions_batch(
        self,
        dimensions: list[dict[str, Any]],
    ) -> int:
        """批量导入维度节点.

        Args:
            dimensions: 维度数据列表

        Returns:
            成功导入的数量
        """
        count = 0
        for dim_data in dimensions:
            try:
                dimension = DimensionNode(
                    dimension_id=dim_data["dimension_id"],
                    name=dim_data["name"],
                    description=dim_data["description"],
                    values=dim_data.get("values", []),
                )

                self.store.create_dimension_node(dimension)
                count += 1
            except Exception as e:
                print(f"  警告: 导入维度 {dim_data.get('dimension_id')} 失败: {e}")

        return count

    def import_domains_batch(
        self,
        domains: list[dict[str, Any]],
    ) -> int:
        """批量导入业务域节点.

        Args:
            domains: 业务域数据列表

        Returns:
            成功导入的数量
        """
        count = 0
        for domain_data in domains:
            try:
                domain = BusinessDomainNode(
                    domain_id=domain_data["domain_id"],
                    name=domain_data["name"],
                    description=domain_data["description"],
                )

                self.store.create_domain_node(domain)
                count += 1
            except Exception as e:
                print(f"  警告: 导入业务域 {domain_data.get('domain_id')} 失败: {e}")

        return count

    def import_relations_batch(
        self,
        relations: list[dict[str, Any]],
    ) -> int:
        """批量导入关系.

        Args:
            relations: 关系数据列表

        Returns:
            成功导入的数量
        """
        count = 0
        for rel_data in relations:
            try:
                rel_type = rel_data["type"]

                if rel_type == "belongs_to_domain":
                    self.store.add_belongs_to_domain(
                        metric_id=rel_data["metric_id"],
                        domain_id=rel_data["domain_id"],
                        weight=rel_data.get("weight", 1.0),
                    )

                elif rel_type == "has_dimension":
                    self.store.add_has_dimension(
                        metric_id=rel_data["metric_id"],
                        dimension_id=rel_data["dimension_id"],
                        required=rel_data.get("required", True),
                    )

                elif rel_type == "derived_from":
                    self.store.add_derived_from(
                        source_metric_id=rel_data["source_metric_id"],
                        target_metric_id=rel_data["target_metric_id"],
                        confidence=rel_data.get("confidence", 0.8),
                        formula=rel_data.get("formula"),
                    )

                elif rel_type == "correlates_with":
                    self.store.add_correlates_with(
                        metric_id_1=rel_data["metric_id_1"],
                        metric_id_2=rel_data["metric_id_2"],
                        weight=rel_data.get("weight", 0.5),
                        correlation_type=rel_data.get("correlation_type", "positive"),
                    )

                count += 1

            except Exception as e:
                print(f"  警告: 导入关系失败: {e}")

        return count


# 示例数据
SAMPLE_METRICS = [
    {
        "metric_id": "m001",
        "name": "GMV",
        "code": "gmv",
        "description": "成交总额",
        "domain": "电商",
        "importance": 0.9,
        "synonyms": ["成交金额", "交易额"],
        "formula": "SUM(order_amount)",
    },
    {
        "metric_id": "m002",
        "name": "DAU",
        "code": "dau",
        "description": "日活跃用户数",
        "domain": "用户",
        "importance": 0.95,
        "synonyms": ["日活"],
        "formula": "COUNT(DISTINCT user_id) WHERE date = TODAY",
    },
    {
        "metric_id": "m003",
        "name": "MAU",
        "code": "mau",
        "description": "月活跃用户数",
        "domain": "用户",
        "importance": 0.9,
        "synonyms": ["月活"],
        "formula": "COUNT(DISTINCT user_id) WHERE date >= TODAY - 30",
    },
    {
        "metric_id": "m004",
        "name": "ARPU",
        "code": "arpu",
        "description": "每用户平均收入",
        "domain": "营收",
        "importance": 0.85,
        "synonyms": ["人均收入"],
        "formula": "total_revenue / active_users",
    },
    {
        "metric_id": "m005",
        "name": "转化率",
        "code": "conversion_rate",
        "description": "访客转化为付费用户的比例",
        "domain": "增长",
        "importance": 0.8,
        "synonyms": ["付费转化率"],
    },
]

SAMPLE_DOMAINS = [
    {"domain_id": "d001", "name": "电商", "description": "电商业务域"},
    {"domain_id": "d002", "name": "用户", "description": "用户相关指标"},
    {"domain_id": "d003", "name": "营收", "description": "营收相关指标"},
    {"domain_id": "d004", "name": "增长", "description": "增长相关指标"},
]

SAMPLE_RELATIONS = [
    {"type": "belongs_to_domain", "metric_id": "m001", "domain_id": "d001"},
    {"type": "belongs_to_domain", "metric_id": "m002", "domain_id": "d002"},
    {"type": "belongs_to_domain", "metric_id": "m003", "domain_id": "d002"},
    {"type": "belongs_to_domain", "metric_id": "m004", "domain_id": "d003"},
    {"type": "belongs_to_domain", "metric_id": "m005", "domain_id": "d004"},
    {"type": "derived_from", "source_metric_id": "m004", "target_metric_id": "m001", "confidence": 0.6},
    {"type": "derived_from", "source_metric_id": "m004", "target_metric_id": "m002"},
    {"type": "correlates_with", "metric_id_1": "m002", "metric_id_2": "m003", "weight": 0.9},
]
