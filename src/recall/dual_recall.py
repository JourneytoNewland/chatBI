"""双路召回融合模块."""

import asyncio
from typing import Any

from src.recall.graph.neo4j_client import Neo4jClient
from src.recall.graph.recall import GraphRecall
from src.recall.vector.qdrant_store import QdrantVectorStore
from src.recall.vector.vectorizer import MetricVectorizer


class DualRecallResult:
    """双路召回结果.

    Attributes:
        metric_id: 指标ID
        name: 指标名称
        code: 指标编码
        description: 业务含义
        domain: 业务域
        score: 相似度分数
        source: 召回来源 (vector/graph/both)
        vector_score: 向量召回分数
        graph_score: 图谱召回分数
    """

    def __init__(
        self,
        metric_id: str,
        name: str,
        code: str,
        description: str,
        domain: str,
        score: float,
        source: str,
        vector_score: float | None = None,
        graph_score: float | None = None,
    ) -> None:
        """初始化召回结果."""
        self.metric_id = metric_id
        self.name = name
        self.code = code
        self.description = description
        self.domain = domain
        self.score = score
        self.source = source
        self.vector_score = vector_score
        self.graph_score = graph_score

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "domain": self.domain,
            "score": self.score,
            "source": self.source,
            "vector_score": self.vector_score,
            "graph_score": self.graph_score,
        }


class DualRecall:
    """双路召回融合器.

    并行执行向量召回和图谱召回，合并去重后返回。
    """

    def __init__(
        self,
        vectorizer: MetricVectorizer,
        vector_store: QdrantVectorStore,
        neo4j_client: Neo4jClient,
    ) -> None:
        """初始化双路召回器.

        Args:
            vectorizer: 向量化器
            vector_store: 向量存储
            neo4j_client: Neo4j 客户端
        """
        self.vectorizer = vectorizer
        self.vector_store = vector_store

        from src.recall.graph.graph_store import GraphStore

        self.graph_store = GraphStore(neo4j_client)
        self.graph_recall = GraphRecall(self.graph_store)

    async def _vector_recall_async(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """异步向量召回.

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            向量召回结果列表
        """
        # 在线程池中执行同步操作
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._vector_recall_sync, query, top_k)

    def _vector_recall_sync(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """同步向量召回实现."""
        try:
            from src.recall.vector.models import MetricMetadata

            print(f"  [DEBUG] 向量召回: 开始向量化查询")
            # 向量化查询
            query_metadata = MetricMetadata(
                name=query,
                code=query,
                description=query,
                synonyms=[],
                domain="查询",
            )
            query_vector = self.vectorizer.vectorize(query_metadata)
            print(f"  [DEBUG] 向量维度: {query_vector.shape}")

            # 向量检索
            print(f"  [DEBUG] 开始 Qdrant 搜索，top_k={top_k}")
            results = self.vector_store.search(query_vector, top_k=top_k)
            print(f"  [DEBUG] Qdrant 返回 {len(results)} 个结果")

            # 格式化结果
            formatted_results = []
            for result in results:
                payload = result["payload"]
                formatted_results.append(
                    {
                        "metric_id": str(payload.get("metric_id", "")),
                        "name": payload.get("metric_name", ""),
                        "code": payload.get("metric_code", ""),
                        "description": payload.get("description", ""),
                        "domain": payload.get("domain", ""),
                        "score": result["score"],
                    }
                )

            return formatted_results
        except Exception as e:
            print(f"  [DEBUG] 向量召回异常: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def _graph_recall_async(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """异步图谱召回.

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            图谱召回结果列表
        """
        # 在线程池中执行同步操作
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._graph_recall_sync, query, top_k)

    def _graph_recall_sync(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """同步图谱召回实现."""
        # 混合召回策略
        results = self.graph_recall.hybrid_recall(query=query, top_k=top_k)

        # 格式化结果
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "metric_id": result["metric_id"],
                    "name": result["name"],
                    "code": result["code"],
                    "description": result["description"],
                    "domain": result.get("domain", ""),
                    "score": 1.0,  # 图谱召回暂时使用默认分数
                }
            )

        return formatted_results

    async def dual_recall(
        self,
        query: str,
        vector_top_k: int = 50,
        graph_top_k: int = 30,
        final_top_k: int = 10,
        timeout: float = 0.5,
    ) -> list[DualRecallResult]:
        """双路召回主函数.

        并行执行向量召回和图谱召回，合并去重。

        Args:
            query: 查询文本
            vector_top_k: 向量召回返回数量
            graph_top_k: 图谱召回返回数量
            final_top_k: 最终返回数量
            timeout: 单路召回超时时间（秒）

        Returns:
            融合后的召回结果列表
        """
        try:
            # 并行执行双路召回
            vector_task = asyncio.wait_for(
                self._vector_recall_async(query, vector_top_k),
                timeout=timeout,
            )
            graph_task = asyncio.wait_for(
                self._graph_recall_async(query, graph_top_k),
                timeout=timeout,
            )

            vector_results, graph_results = await asyncio.gather(
                vector_task,
                graph_task,
                return_exceptions=True,
            )

            # 处理异常
            if isinstance(vector_results, Exception):
                print(f"向量召回失败: {vector_results}")
                vector_results = []
            if isinstance(graph_results, Exception):
                print(f"图谱召回失败: {graph_results}")
                graph_results = []

        except asyncio.TimeoutError:
            print("双路召回超时")
            vector_results = []
            graph_results = []

        # 合并去重
        merged_results = self._merge_results(
            vector_results,
            graph_results,
        )

        # 按分数排序并返回 Top-K
        merged_results.sort(key=lambda x: x.score, reverse=True)
        return merged_results[:final_top_k]

    def _merge_results(
        self,
        vector_results: list[dict[str, Any]],
        graph_results: list[dict[str, Any]],
    ) -> list[DualRecallResult]:
        """合并向量召回和图谱召回结果.

        Args:
            vector_results: 向量召回结果
            graph_results: 图谱召回结果

        Returns:
            合并后的结果列表
        """
        # 使用字典记录 metric_id -> 结果
        merged_map: dict[str, DualRecallResult] = {}

        # 处理向量召回结果
        for result in vector_results:
            metric_id = result["metric_id"]
            merged_map[metric_id] = DualRecallResult(
                metric_id=metric_id,
                name=result["name"],
                code=result["code"],
                description=result["description"],
                domain=result["domain"],
                score=result["score"],
                source="vector",
                vector_score=result["score"],
                graph_score=None,
            )

        # 处理图谱召回结果（合并或新增）
        for result in graph_results:
            metric_id = result["metric_id"]

            if metric_id in merged_map:
                # 已存在：合并分数
                existing = merged_map[metric_id]
                existing.source = "both"
                existing.graph_score = 1.0
                # 加权融合：向量 0.7 + 图谱 0.3
                existing.score = existing.vector_score * 0.7 + 0.3
            else:
                # 不存在：新增
                merged_map[metric_id] = DualRecallResult(
                    metric_id=metric_id,
                    name=result["name"],
                    code=result["code"],
                    description=result["description"],
                    domain=result["domain"],
                    score=0.7,  # 图谱召回默认分数
                    source="graph",
                    vector_score=None,
                    graph_score=1.0,
                )

        return list(merged_map.values())
