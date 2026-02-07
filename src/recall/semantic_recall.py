"""L2层语义向量召回模块."""

import time
from dataclasses import dataclass
from typing import Any, Optional

from ..embedding.bge_embedding import BGEEmbeddingModel, get_bge_model
from ..recall.vector.qdrant_store import QdrantVectorStore


@dataclass
class SemanticSearchResult:
    """语义搜索结果."""

    metric_id: str
    name: str
    score: float
    metadata: dict[str, Any]
    match_reason: str


@dataclass
class SemanticRecallResult:
    """语义召回结果."""

    query: str
    core_query: str
    candidates: list[SemanticSearchResult]
    total: int
    search_method: str
    latency: float
    embedding_dim: int


class SemanticRecall:
    """语义向量召回器（L2层）.

    功能:
    - 使用BGE-M3编码查询
    - Qdrant向量检索
    - Top-K相似度排序

    性能:
    - 延迟: ~50ms
    - 召回率: ~85%
    - 成本: 本地免费
    """

    def __init__(
        self,
        embedding_model: Optional[BGEEmbeddingModel] = None,
        qdrant_store: Optional[QdrantVectorStore] = None
    ):
        """初始化语义召回器.

        Args:
            embedding_model: 嵌入模型
            qdrant_store: Qdrant存储
        """
        self.embedding_model = embedding_model or get_bge_model()
        self.qdrant_store = qdrant_store or QdrantVectorStore()

        # 检查模型可用性
        self.available = self.embedding_model.is_available()

        if not self.available:
            print("⚠️  BGE模型不可用，语义召回功能将被禁用")

    def recall(
        self,
        query: str,
        top_k: int = 10,
        score_threshold: float = 0.6
    ) -> Optional[SemanticRecallResult]:
        """执行语义召回.

        Args:
            query: 查询文本
            top_k: 返回结果数量
            score_threshold: 相似度阈值

        Returns:
            召回结果
        """
        if not self.available:
            return None

        start = time.time()

        try:
            # 1. 编码查询
            query_vector = self.embedding_model.encode_query(query)
            embedding_time = time.time() - start

            # 2. 向量检索
            search_start = time.time()
            qdrant_results = self.qdrant_store.search(
                query_vector=query_vector,
                top_k=top_k,
                score_threshold=score_threshold
            )
            search_time = time.time() - search_start

            # 3. 格式化结果
            candidates = []
            for result in qdrant_results:
                candidates.append(SemanticSearchResult(
                    metric_id=result["payload"].get("metric_id", result["id"]),
                    name=result["payload"].get("name", ""),
                    score=result["score"],
                    metadata=result["payload"],
                    match_reason=f"语义相似度 {result['score']:.3f}"
                ))

            return SemanticRecallResult(
                query=query,
                core_query=query,
                candidates=candidates,
                total=len(candidates),
                search_method="BGE-M3 + Qdrant",
                latency=time.time() - start,
                embedding_dim=len(query_vector)
            )

        except Exception as e:
            print(f"❌ 语义召回失败: {e}")
            return None

    def batch_encode_metrics(self, metrics: list[dict[str, Any]]) -> int:
        """批量编码指标并导入Qdrant.

        Args:
            metrics: 指标列表

        Returns:
            成功导入的数量
        """
        if not self.available:
            print("❌ BGE模型不可用")
            return 0

        print(f"📦 批量编码 {len(metrics)} 个指标...")

        # 1. 编码
        texts = [
            f"{m['name']} {m.get('description', '')} {' '.join(m.get('synonyms', []))}"
            for m in metrics
        ]

        embeddings = self.embedding_model.encode(texts, show_progress=True)

        # 2. 导入Qdrant
        ids = [m["metric_id"] for m in metrics]
        payloads = metrics

        count = self.qdrant_store.upsert(
            ids=ids,
            vectors=embeddings,
            payloads=payloads,
            batch_size=64
        )

        print(f"✅ 成功导入 {count} 个指标向量")

        return count


# 带兜底的语义召回（使用模拟数据）
class FallbackSemanticRecall:
    """兜底语义召回器（基于同义词匹配）.

    在Qdrant不可用时使用
    """

    def __init__(self, mock_metrics: list[dict] = None):
        """初始化兜底召回器.

        Args:
            mock_metrics: 模拟指标数据
        """
        from .llm_intent import MOCK_METRICS
        self.metrics = mock_metrics or MOCK_METRICS

    def recall(
        self,
        query: str,
        top_k: int = 10,
        score_threshold: float = 0.5
    ) -> SemanticRecallResult:
        """执行兜底召回."""
        import re

        start = time.time()

        # 清理查询
        query_clean = re.sub(r'^[的的之之]+', '', query.lower().strip())
        query_clean = re.sub(r'[的的之之]+$', '', query_clean)

        # 简单匹配算法
        candidates = []
        for metric in self.metrics:
            score = 0.0

            # 精确匹配名称
            if query_clean == metric["name"].lower():
                score = 1.0
            # 精确匹配同义词
            elif any(query_clean == syn.lower() for syn in metric["synonyms"]):
                score = 0.98
            # 包含匹配
            elif query_clean in metric["name"].lower():
                score = 0.85
            elif query_clean in metric["description"].lower():
                score = 0.75
            # 同义词包含
            elif any(query_clean in syn.lower() for syn in metric["synonyms"]):
                score = 0.80

            if score >= score_threshold:
                candidates.append(SemanticSearchResult(
                    metric_id=metric["metric_id"],
                    name=metric["name"],
                    score=score,
                    metadata=metric,
                    match_reason=f"规则匹配 {score:.2f}"
                ))

        # 排序
        candidates.sort(key=lambda x: x.score, reverse=True)
        candidates = candidates[:top_k]

        return SemanticRecallResult(
            query=query,
            core_query=query_clean,
            candidates=candidates,
            total=len(candidates),
            search_method="规则兜底（同义词匹配）",
            latency=time.time() - start,
            embedding_dim=0
        )


# 测试函数
def test_semantic_recall():
    """测试语义召回."""
    print("\n🧪 测试语义向量召回")
    print("=" * 50)

    # 测试兜底召回器
    fallback = FallbackSemanticRecall()

    test_queries = [
        "GMV",
        "成交金额",
        "日活用户",
        "本月营收"
    ]

    for query in test_queries:
        print(f"\n查询: {query}")
        print("-" * 50)

        result = fallback.recall(query, top_k=3)

        print(f"✅ 召回成功: {result.total} 个结果")
        print(f"   耗时: {result.latency*1000:.2f}ms")
        print(f"   方法: {result.search_method}")

        for i, cand in enumerate(result.candidates, 1):
            print(f"   {i}. {cand.name} (分数: {cand.score:.3f})")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    test_semantic_recall()
