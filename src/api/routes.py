"""检索 API 路由."""

import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from qdrant_client.http.exceptions import UnexpectedResponse

from src.api.models import MetricCandidate, SearchRequest, SearchResponse
from src.config import settings
from src.recall.vector.models import MetricMetadata
from src.recall.vector.qdrant_store import QdrantVectorStore
from src.recall.vector.vectorizer import MetricVectorizer

router = APIRouter()

# 全局向量化器实例
_vectorizer: Optional[MetricVectorizer] = None


def get_vectorizer() -> MetricVectorizer:
    """获取向量化器实例（单例）.

    Returns:
        MetricVectorizer 实例
    """
    global _vectorizer
    if _vectorizer is None:
        _vectorizer = MetricVectorizer(model_name=settings.vectorizer.model_name)
    return _vectorizer


@router.post("/search", response_model=SearchResponse)
async def search_metrics(request: Request, search_req: SearchRequest) -> SearchResponse:
    """语义检索指标.

    Args:
        request: FastAPI Request 对象
        search_req: 检索请求

    Returns:
        检索响应，包含候选指标列表和执行时间

    Raises:
        HTTPException: 当检索失败时抛出
    """
    start_time = time.time()

    # 获取 vector_store（从应用状态）
    vector_store: QdrantVectorStore = getattr(request.app.state, "vector_store", None)
    if vector_store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="向量存储服务未初始化",
        )

    try:
        # 1. 将查询文本向量化
        vectorizer = get_vectorizer()
        query_metadata = MetricMetadata(
            name=search_req.query,
            code=search_req.query,
            description=search_req.query,
            synonyms=[],
            domain="查询",
        )
        query_vector = vectorizer.vectorize(query_metadata)

        # 2. 在 Qdrant 中检索
        results = vector_store.search(
            query_vector=query_vector,
            top_k=search_req.top_k,
            score_threshold=search_req.score_threshold,
        )

        # 3. 格式化候选结果
        candidates = [
            MetricCandidate(
                metric_id=result["payload"]["metric_id"],
                name=result["payload"]["name"],
                code=result["payload"]["code"],
                description=result["payload"]["description"],
                domain=result["payload"]["domain"],
                score=result["score"],
                synonyms=result["payload"].get("synonyms", []),
                formula=result["payload"].get("formula"),
            )
            for result in results
        ]

        # 4. 计算执行时间
        execution_time = (time.time() - start_time) * 1000  # 转换为毫秒

        return SearchResponse(
            query=search_req.query,
            candidates=candidates,
            total=len(candidates),
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
