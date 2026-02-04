"""图谱召回算法."""

from typing import Any

from src.recall.graph.graph_store import GraphStore


class GraphRecall:
    """基于图谱的召回算法.

    利用图谱中的节点关系进行指标召回。
    """

    def __init__(self, graph_store: GraphStore) -> None:
        """初始化图谱召回器.

        Args:
            graph_store: 图谱存储实例
        """
        self.store = graph_store

    def recall_by_text_match(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """基于文本匹配召回.

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            召回的指标列表
        """
        results = self.store.find_metrics_by_name_or_synonym(query)
        return results[:top_k]

    def recall_by_domain(
        self,
        domain_name: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """基于业务域召回.

        Args:
            domain_name: 业务域名称
            top_k: 返回数量

        Returns:
            召回的指标列表
        """
        results = self.store.find_metrics_by_domain(domain_name)
        return results[:top_k]

    def recall_by_relation(
        self,
        metric_id: str,
        relation_types: list[str] | None = None,
        max_depth: int = 2,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """基于关系路径召回.

        Args:
            metric_id: 起始指标 ID
            relation_types: 关系类型过滤（可选）
            max_depth: 最大路径深度
            top_k: 返回数量

        Returns:
            召回的相关指标列表
        """
        results = self.store.find_related_metrics(
            metric_id=metric_id,
            relation_types=relation_types,
            max_depth=max_depth,
        )
        return results[:top_k]

    def hybrid_recall(
        self,
        query: str,
        metric_id: str | None = None,
        domain_name: str | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """混合召回策略.

        结合多种召回策略，合并去重后返回。

        Args:
            query: 查询文本
            metric_id: 指标 ID（用于关系召回）
            domain_name: 业务域名称（用于域召回）
            top_k: 返回数量

        Returns:
            召回的指标列表
        """
        all_results = []

        # 1. 文本匹配召回
        if query:
            text_results = self.recall_by_text_match(query, top_k=top_k)
            all_results.extend(text_results)

        # 2. 业务域召回
        if domain_name:
            domain_results = self.recall_by_domain(domain_name, top_k=top_k)
            all_results.extend(domain_results)

        # 3. 关系召回
        if metric_id:
            relation_results = self.recall_by_relation(
                metric_id=metric_id,
                top_k=top_k,
            )
            all_results.extend(relation_results)

        # 去重（保留第一次出现的）
        seen = set()
        unique_results = []
        for result in all_results:
            metric_id = result.get("metric_id")
            if metric_id and metric_id not in seen:
                seen.add(metric_id)
                unique_results.append(result)

        return unique_results[:top_k]

    def expand_query_with_synonyms(
        self,
        query: str,
    ) -> list[str]:
        """使用同义词扩展查询.

        Args:
            query: 原始查询

        Returns:
            扩展后的查询列表
        """
        # 查找包含 query 文本的指标，提取同义词
        metrics = self.store.find_metrics_by_name_or_synonym(query)

        synonyms = set()
        synonyms.add(query)

        for metric in metrics:
            metric_data = metric.get("m", {})
            if metric_data:
                synonym_list = metric_data.get("synonyms", [])
                synonyms.update(synonym_list)

        return list(synonyms)
