"""检索 API 路由."""

import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from qdrant_client.http.exceptions import UnexpectedResponse

from src.api.models import MetricCandidate, SearchRequest, SearchResponse
from src.config import settings
from src.recall.dual_recall import DualRecall, DualRecallResult
from src.recall.graph.neo4j_client import Neo4jClient
from src.recall.vector.models import MetricMetadata
from src.recall.vector.qdrant_store import QdrantVectorStore
from src.recall.vector.vectorizer import MetricVectorizer
from src.rerank.models import Candidate, QueryContext
from src.rerank.ranker import RuleBasedRanker
from src.validator.validators import ValidationPipeline

router = APIRouter()

# 全局实例
_vectorizer: Optional[MetricVectorizer] = None
_ranker: Optional[RuleBasedRanker] = None
_validator: Optional[ValidationPipeline] = None


def get_vectorizer() -> MetricVectorizer:
    """获取向量化器实例（单例）."""
    global _vectorizer
    if _vectorizer is None:
        _vectorizer = MetricVectorizer(model_name=settings.vectorizer.model_name)
    return _vectorizer


def get_ranker() -> RuleBasedRanker:
    """获取打分器实例（单例）."""
    global _ranker
    if _ranker is None:
        _ranker = RuleBasedRanker()
    return _ranker


def get_validator() -> ValidationPipeline:
    """获取验证器实例（单例）."""
    global _validator
    if _validator is None:
        _validator = ValidationPipeline()
    return _validator


@router.post("/search", response_model=SearchResponse)
async def search_metrics(request: Request, search_req: SearchRequest) -> SearchResponse:
    """智能检索指标（双路召回 + 精排 + 验证）.

    Args:
        request: FastAPI Request 对象
        search_req: 检索请求

    Returns:
        检索响应，包含候选指标列表和执行时间

    Raises:
        HTTPException: 当检索失败时抛出
    """
    start_time = time.time()

    # 获取服务实例
    vector_store: QdrantVectorStore = getattr(request.app.state, "vector_store", None)
    neo4j_client: Neo4jClient = getattr(request.app.state, "neo4j_client", None)

    if vector_store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="向量存储服务未初始化",
        )

    try:
        vectorizer = get_vectorizer()
        ranker = get_ranker()
        validator = get_validator()

        # 1. 双路召回
        if neo4j_client is not None:
            # 双路召回模式
            dual_recall = DualRecall(vectorizer, vector_store, neo4j_client)
            recall_results = await dual_recall.dual_recall(
                query=search_req.query,
                vector_top_k=search_req.top_k * 2,  # 召回更多候选
                graph_top_k=search_req.top_k,
                final_top_k=search_req.top_k * 2,
            )
        else:
            # 仅向量召回模式（兼容性）
            query_metadata = MetricMetadata(
                name=search_req.query,
                code=search_req.query,
                description=search_req.query,
                synonyms=[],
                domain="查询",
            )
            query_vector = vectorizer.vectorize(query_metadata)
            raw_results = vector_store.search(
                query_vector=query_vector,
                top_k=search_req.top_k * 2,
                score_threshold=search_req.score_threshold,
            )

            # 转换为 DualRecallResult
            recall_results = []
            for result in raw_results:
                payload = result["payload"]
                recall_results.append(
                    DualRecallResult(
                        metric_id=payload["metric_id"],
                        name=payload["name"],
                        code=payload["code"],
                        description=payload["description"],
                        domain=payload.get("domain", ""),
                        score=result["score"],
                        source="vector",
                        vector_score=result["score"],
                        graph_score=0.0,
                    )
                )

        # 2. 转换为 Candidate
        candidates = []
        for result in recall_results:
            candidates.append(
                Candidate(
                    metric_id=result.metric_id,
                    name=result.name,
                    code=result.code,
                    description=result.description,
                    domain=result.domain,
                    synonyms=[],  # 从向量存储获取
                    importance=0.5,  # 默认重要性
                    formula=None,  # 从向量存储获取
                    vector_score=result.vector_score or 0.0,
                    graph_score=result.graph_score or 0.0,
                    source=result.source,
                )
            )

        # 3. 精排
        context = QueryContext.from_text(search_req.query)
        ranked_results = ranker.rerank(candidates, context, top_k=search_req.top_k)

        # 4. 验证并格式化结果
        final_candidates = []
        for candidate, score, _ in ranked_results:
            # 运行验证器
            validation_results = validator.validate(candidate, context)

            # 只保留未 FAILED 的结果
            if not validator.has_failed(validation_results):
                final_candidates.append(
                    MetricCandidate(
                        metric_id=candidate.metric_id,
                        name=candidate.name,
                        code=candidate.code,
                        description=candidate.description,
                        domain=candidate.domain,
                        score=score,
                        synonyms=candidate.synonyms,
                        formula=candidate.formula,
                    )
                )

        # 5. 计算执行时间
        execution_time = (time.time() - start_time) * 1000

        return SearchResponse(
            query=search_req.query,
            candidates=final_candidates,
            total=len(final_candidates),
            execution_time=round(execution_time, 2),
        )

    except UnexpectedResponse as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"向量检索失败: {e}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检索过程中发生错误: {e}",
        ) from e
