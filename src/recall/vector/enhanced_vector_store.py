"""增强的向量库存储 - 支持多粒度文本."""

from typing import Any, Dict, List, Optional

from qdrant_client.models import Distance, PointStruct, Filter, FieldCondition, MatchValue
from qdrant_client.qdrant_client import models

from src.recall.vector.models import MetricMetadata
from src.recall.vector.vectorizer import MetricVectorizer


class EnhancedQdrantVectorStore:
    """增强的Qdrant向量库存储 - 支持多粒度文本和摘要.

    特性：
    1. 多粒度文本存储：业务摘要、LLM文本、RAG文档
    2. 元数据过滤：按业务域、文本类型过滤
    3. 混合检索：向量检索 + 元数据过滤
    """

    def __init__(
        self,
        url: str,
        collection_name: str = "metrics_enhanced",
        vector_size: int = 768,
        vectorizer: Optional[MetricVectorizer] = None
    ):
        """初始化向量库存储.

        Args:
            url: Qdrant服务器地址
            collection_name: 集合名称
            vector_size: 向量维度
            vectorizer: 向量化器（可选）
        """
        from qdrant_client import QdrantClient

        self.qdrant_client = QdrantClient(url=url, timeout=60)
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.vectorizer = vectorizer or MetricVectorizer()

        # 创建集合（如果不存在）
        self._create_collection_if_not_exists()

    def _create_collection_if_not_exists(self):
        """创建集合（如果不存在）."""
        from qdrant_client.models import Distance, VectorParams, Range

        collections = self.qdrant_client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
                optimizers_config=models.OptimizersConfigConfig(indexing_params=models.IndexingParams(
                    metric=Distance.COSINE
                )
            )
            print(f"✅ 创建集合: {self.collection_name}")
        else:
            print(f"✅ 集合已存在: {self.collection_name}")

    def upsert_metric_with_summaries(
        self,
        metric_id: str,
        metadata: MetricMetadata,
        summaries: Dict[str, str]
    ):
        """入库多粒度文本向量.

        Args:
            metric_id: 指标ID（通常是 code）
            metadata: 指标元数据
            summaries: {
                "business_summary": "业务摘要",
                "llm_friendly_text": "LLM友好文本",
                "rag_document": "RAG文档"
            }
        """
        points = []

        # 为每种摘要类型生成向量
        for summary_type, text in summaries.items():
            if not text:
                continue

            # 向量化文本
            vector = self.vectorizer.vectorize_text(text)

            # 创建点
            point_id = f"{metric_id}_{summary_type}"
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector.tolist(),
                    payload={
                        "metric_id": metric_id,
                        "text_type": summary_type,  # business_summary / llm_friendly / rag
                        "text": text,
                        "metadata": metadata.dict(),
                        "timestamp": self._get_timestamp(),
                    }
                )
            )

        # 批量入库
        if points:
            operation_info = self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            print(f"✅ 指标 {metric_id} 入库成功：{len(points)} 个向量点")
            return operation_info

        return None

    def search_with_filters(
        self,
        query_text: str,
        text_type: Optional[str] = None,  # 按文本类型过滤
        domain: Optional[str] = None,  # 按业务域过滤
        top_k: int = 10,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """带过滤的向量搜索.

        Args:
            query_text: 查询文本
            text_type: 文本类型过滤
            domain: 业务域过滤
            top_k: 返回数量
            score_threshold: 相似度阈值

        Returns:
            搜索结果列表
        """
        # 1. 向量化查询文本
        query_vector = self.vectorizer.vectorize_text(query_text)

        # 2. 构建过滤条件
        query_filter = None

        if text_type or domain:
            must_conditions = []

            if text_type:
                must_conditions.append(
                    FieldCondition(
                        key="text_type",
                        match=MatchValue(value=text_type)
                    )
                )

            if domain:
                must_conditions.append(
                    FieldCondition(
                        key="metadata.domain",
                        match=MatchValue(value=domain)
                    )
                )

            if must_conditions:
                query_filter = Filter(must=must_conditions)

        # 3. 搜索
        search_results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_vector.tolist(),
            limit=top_k,
            query_filter=query_filter,
            score_threshold=score_threshold
        )

        # 4. 格式化结果
        results = []
        for result in search_results:
            results.append({
                "id": result.id,
                "score": result.score,
                "metric_id": result.payload.get("metric_id"),
                "text_type": result.payload.get("text_type"),
                "text": result.payload.get("text"),
                "metadata": result.payload.get("metadata"),
            })

        return results

    def search_all_text_types(
        self,
        query_text: str,
        metric_id: str,
        top_k: int = 10
    ) -> Dict[str, List[Dict[str, Any]]):
        """搜索某个指标的所有文本类型.

        Args:
            query_text: 查询文本
            metric_id: 指标ID
            top_k: 每种类型返回的最大数量

        Returns:
            按文本类型分组的结果
        """
        query_vector = self.vectorizer.vectorize_text(query_text)

        # 构建过滤条件：只查询指定指标的所有文本类型
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="metric_id",
                    match=MatchValue(value=metric_id)
                )
            ]
        )

        # 搜索
        search_results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_vector.tolist(),
            limit=top_k * 3,  # 3种文本类型
            query_filter=query_filter
        )

        # 按文本类型分组
        grouped_results = {
            "business_summary": [],
            "llm_friendly": [],
            "rag_document": []
        }

        for result in search_results:
            text_type = result.payload.get("text_type")
            if text_type in grouped_results:
                grouped_results[text_type].append({
                    "id": result.id,
                    "score": result.score,
                    "text": result.payload.get("text"),
                })

        return grouped_results

    def delete_metric(self, metric_id: str):
        """删除指标的所有向量点.

        Args:
            metric_id: 指标ID
        """
        # 构建过滤条件
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="metric_id",
                    match=MatchValue(value=metric_id)
                )
            ]
        )

        # 删除
        self.qdrant_client.delete(
            collection_name=self.collection_name,
            query_filter=query_filter
        )
        print(f"✅ 删除指标 {metric_id} 的所有向量点")

    def _get_timestamp(self) -> int:
        """获取当前时间戳（毫秒）."""
        import time
        return int(time.time() * 1000)


# ========== 辅助函数 ==========

def _generate_fallback_summaries(metadata: MetricMetadata) -> Dict[str, str]:
    """生成默认摘要（当 GLM 不可用时）."""
    return {
        "business_summary": f"{metadata.name}是{metadata.domain}域的核心指标，用于{metadata.description}。",
        "llm_friendly_text": f"Metric: {metadata.name}, Code: {metadata.code}, Domain: {metadata.domain}, Description: {metadata.description}.",
        "rag_document": f"# {metadata.name}\n\n## 业务定义\n{metadata.description}\n\n## 计算方法\n{metadata.formula or '详见计算文档'}",
    }
