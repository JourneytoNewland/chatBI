"""图谱和向量库管理API - 支持GLM摘要生成."""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.config import settings
from src.services.summary_service import GLMSummaryService
from src.recall.graph.graph_store import GraphStore
from src.recall.graph.models import MetricNode
from src.recall.graph.neo4j_client import Neo4jClient
from src.recall.vector.models import MetricMetadata
from src.recall.vector.qdrant_store import QdrantVectorStore
from src.recall.vector.vectorizer import MetricVectorizer


# ========== 请求/响应模型 ==========


class MetricMetadataInput(BaseModel):
    """指标元数据输入模型."""

    name: str = Field(..., description="指标名称")
    code: str = Field(..., description="指标编码")
    description: str = Field(..., description="业务含义")
    synonyms: List[str] = Field(default_factory=list, description="同义词列表")
    domain: str = Field(..., description="业务域")
    formula: Optional[str] = Field(None, description="计算公式")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="重要性（0-1）")


class MetricBatchImportRequest(BaseModel):
    """批量导入指标请求."""

    metrics: List[MetricMetadataInput] = Field(..., description="指标列表")
    generate_summary: bool = Field(default=True, description="是否生成GLM摘要")
    summary_llm_model: str = Field(default="glm-4-flash", description="摘要生成模型")
    index_to_vector: bool = Field(default=True, description="是否索引到向量库")
    index_to_graph: bool = Field(default=True, description="是否索引到图谱库")
    batch_size: int = Field(default=5, ge=1, le=10, description="摘要生成批大小")


class ImportResult(BaseModel):
    """导入结果."""

    total: int = Field(..., description="总数")
    success: int = Field(..., description="成功数")
    failed: int = Field(..., description="失败数")
    failed_ids: List[str] = Field(default_factory=list, description="失败的指标ID")
    execution_time_ms: float = Field(..., description="执行时间（毫秒）")
    task_id: Optional[str] = Field(None, description="异步任务ID")


class TaskStatus(BaseModel):
    """任务状态."""

    task_id: str
    status: str  # pending, processing, completed, failed
    progress: float  # 0-1
    total: int
    completed: int
    result: Optional[ImportResult] = None
    error: Optional[str] = None


# ========== 全局变量 ==========

# 任务存储（生产环境应使用 Redis）
_tasks: Dict[str, TaskStatus] = {}

# 全局服务实例
_summary_service: Optional[GLMSummaryService] = None


# ========== 路由定义 ==========

router = APIRouter(prefix="/api/v1/management", tags=["data-management"])


def get_summary_service() -> Optional[GLMSummaryService]:
    """获取摘要生成服务实例（单例）."""
    global _summary_service
    if _summary_service is None:
        if not settings.zhipuai.api_key:
            print("⚠️  ZHIPUAI_API_KEY 未配置")
            return None
        _summary_service = GLMSummaryService(api_key=settings.zhipuai.api_key)
    return _summary_service


def get_services_from_request(request: Request) -> tuple[QdrantVectorStore, Optional[Neo4jClient], Optional[GraphStore]]:
    """从 Request 对象获取服务实例.

    Args:
        request: FastAPI Request 对象

    Returns:
        (vector_store, neo4j_client, graph_store)
    """
    vector_store: QdrantVectorStore = getattr(request.app.state, "vector_store", None)
    neo4j_client: Optional[Neo4jClient] = getattr(request.app.state, "neo4j_client", None)
    graph_store: Optional[GraphStore] = None

    if vector_store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="向量存储服务未初始化"
        )

    if neo4j_client:
        graph_store = GraphStore(neo4j_client)

    return vector_store, neo4j_client, graph_store


@router.post("/metrics/batch-import", response_model=ImportResult, status_code=status.HTTP_202_ACCEPTED)
async def batch_import_metrics(
    request: MetricBatchImportRequest,
    background_tasks: BackgroundTasks,
    http_request: Request
):
    """批量导入指标到图谱和向量库（异步）.

    工作流程：
    1. 数据验证和清洗
    2. 生成GLM摘要（可选）
    3. 入库到Neo4j图谱库
    4. 向量化并入库到Qdrant向量库
    5. 返回任务ID

    Args:
        request: 批量导入请求
        background_tasks: FastAPI 后台任务
        http_request: FastAPI Request 对象

    Returns:
        导入结果（包含 task_id 用于查询进度）
    """
    start = time.time()

    # 生成任务ID
    task_id = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

    # 转换为内部格式
    metrics_data = [metric.dict() for metric in request.metrics]

    # 初始化任务状态
    _tasks[task_id] = TaskStatus(
        task_id=task_id,
        status="pending",
        progress=0.0,
        total=len(metrics_data),
        completed=0,
        result=None,
        error=None
    )

    # 添加后台任务
    background_tasks.add_task(
        _process_batch_import,
        task_id,
        metrics_data,
        request.generate_summary,
        request.index_to_graph,
        request.index_to_vector,
        request.batch_size,
        http_request  # 传递 Request 对象
    )

    execution_time = (time.time() - start) * 1000

    return ImportResult(
        total=len(request.metrics),
        success=0,
        failed=0,
        failed_ids=[],
        execution_time_ms=round(execution_time, 2),
        task_id=task_id
    )


async def _process_batch_import(
    task_id: str,
    metrics_data: List[Dict[str, Any]],
    generate_summary: bool,
    index_to_graph: bool,
    index_to_vector: bool,
    batch_size: int,
    request: Request  # 添加 Request 参数
):
    """后台批量导入任务."""
    task = _tasks[task_id]
    task.status = "processing"
    task.progress = 0.0

    success_count = 0
    failed_ids = []

    try:
        # 获取服务实例
        vector_store, neo4j_client, graph_store = get_services_from_request(request)

        # 1. 生成GLM摘要
        summaries = []
        if generate_summary:
            summary_service = get_summary_service()
            if summary_service:
                print(f"[{task_id}] 开始生成 {len(metrics_data)} 个指标的GLM摘要...")
                summaries = await summary_service.batch_generate_summaries(
                    metrics=metrics_data,
                    batch_size=batch_size,
                    show_progress=False
                )
            else:
                print(f"[{task_id}] GLM 服务未配置，使用默认摘要")
                summaries = [{} for _ in metrics_data]
        else:
            summaries = [{} for _ in metrics_data]

        task.progress = 0.3

        # 2. 入库到图谱库
        if index_to_graph and graph_store:
            print(f"[{task_id}] 开始入库到 Neo4j 图谱库...")

            for i, metric_data in enumerate(metrics_data):
                try:
                    # 创建指标节点
                    metric_node = MetricNode(
                        metric_id=metric_data["code"],
                        name=metric_data["name"],
                        code=metric_data["code"],
                        description=metric_data["description"],
                        domain=metric_data["domain"],
                        importance=metric_data.get("importance", 0.5),
                        synonyms=metric_data.get("synonyms", []),
                        formula=metric_data.get("formula")
                    )

                    graph_store.create_metric_node(metric_node)
                    success_count += 1

                    # 更新进度
                    task.progress = 0.3 + 0.3 * (i + 1) / len(metrics_data)

                except Exception as e:
                    print(f"[{task_id}] 指标 {metric_data['code']} 入库图谱失败: {e}")
                    failed_ids.append(metric_data["code"])

        task.progress = 0.6

        # 3. 向量化并入库到向量库
        if index_to_vector:
            print(f"[{task_id}] 开始向量化并入库到 Qdrant...")

            vectorizer = request.app.state.vectorizer

            for i, (metric_data, summary) in enumerate(zip(metrics_data, summaries)):
                try:
                    # 构建完整的 MetricMetadata 对象用于向量化
                    # 使用 llm_friendly_text 或默认文本作为 description
                    text_to_vector = summary.get("llm_friendly_text") if summary else None
                    if text_to_vector:
                        # 如果有 GLM 生成的文本，使用它来构建临时元数据
                        temp_metadata = MetricMetadata(
                            name=metric_data["name"],
                            code=metric_data["code"],
                            description=text_to_vector,  # 使用 GLM 生成的文本
                            domain=metric_data["domain"],
                            synonyms=metric_data.get("synonyms", []),
                            formula=metric_data.get("formula")
                        )
                    else:
                        # 否则使用原始元数据
                        temp_metadata = MetricMetadata(
                            name=metric_data["name"],
                            code=metric_data["code"],
                            description=metric_data["description"],
                            domain=metric_data["domain"],
                            synonyms=metric_data.get("synonyms", []),
                            formula=metric_data.get("formula")
                        )

                    # 向量化
                    vector = vectorizer.vectorize(temp_metadata)

                    # 构建 payload（保存原始元数据）
                    payload = {
                        "metric_id": metric_data["code"],
                        "name": metric_data["name"],
                        "code": metric_data["code"],
                        "description": metric_data["description"],
                        "domain": metric_data["domain"],
                        "synonyms": metric_data.get("synonyms", []),
                        "formula": metric_data.get("formula", ""),
                    }

                    # 入库
                    vector_store.upsert(
                        ids=[metric_data["code"]],
                        vectors=[vector.tolist()],
                        payloads=[payload]
                    )

                    # 更新进度
                    task.progress = 0.6 + 0.4 * (i + 1) / len(metrics_data)

                except Exception as e:
                    print(f"[{task_id}] 指标 {metric_data['code']} 向量入库失败: {e}")
                    if metric_data["code"] not in failed_ids:
                        failed_ids.append(metric_data["code"])

        # 完成
        task.status = "completed"
        task.progress = 1.0
        task.completed = success_count
        task.result = ImportResult(
            total=len(metrics_data),
            success=success_count,
            failed=len(failed_ids),
            failed_ids=failed_ids,
            execution_time_ms=0.0,
            task_id=task_id
        )

        print(f"[{task_id}] 批量导入完成：成功 {success_count}，失败 {len(failed_ids)}")

    except Exception as e:
        task.status = "failed"
        task.error = str(e)
        print(f"[{task_id}] 批量导入失败: {e}")


@router.post("/metrics/single")
async def create_single_metric(metric: MetricMetadataInput, request: Request):
    """创建单个指标（包含图谱和向量化）.

    Args:
        metric: 指标元数据
        request: FastAPI Request 对象

    Returns:
        创建结果
    """
    try:
        # 获取服务实例
        vector_store, neo4j_client, graph_store = get_services_from_request(request)

        metric_data = metric.dict()

        # 1. 生成GLM摘要
        summary_service = get_summary_service()
        summary = {}
        if summary_service:
            summary = await summary_service.generate_metric_summaries(metric_data)
        else:
            print("GLM 服务未配置，跳过摘要生成")

        # 2. 入库到图谱库
        if graph_store:
            metric_node = MetricNode(
                metric_id=metric.code,
                name=metric.name,
                code=metric.code,
                description=metric.description,
                domain=metric.domain,
                importance=metric.importance,
                synonyms=metric.synonyms,
                formula=metric.formula
            )
            graph_store.create_metric_node(metric_node)

        # 3. 向量化并入库到向量库
        text_to_vector = summary.get("llm_friendly_text") if summary else None
        if text_to_vector:
            # 使用 GLM 生成的文本
            temp_metadata = MetricMetadata(
                name=metric.name,
                code=metric.code,
                description=text_to_vector,
                domain=metric.domain,
                synonyms=metric.synonyms,
                formula=metric.formula
            )
        else:
            # 使用原始元数据
            temp_metadata = MetricMetadata(
                name=metric.name,
                code=metric.code,
                description=metric.description,
                domain=metric.domain,
                synonyms=metric.synonyms,
                formula=metric.formula
            )

        vector = request.app.state.vectorizer.vectorize(temp_metadata)

        payload = {
            "metric_id": metric.code,
            "name": metric.name,
            "code": metric.code,
            "description": metric.description,
            "domain": metric.domain,
            "synonyms": metric.synonyms,
            "formula": metric.formula or "",
        }

        vector_store.upsert(
            ids=[metric.code],
            vectors=[vector.tolist()],
            payloads=[payload]
        )

        return {
            "success": True,
            "metric_id": metric.code,
            "summary": summary,
            "message": "指标创建成功"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建指标失败: {e}"
        ) from e


@router.get("/metrics/{metric_id}")
async def get_metric(metric_id: str, request: Request):
    """获取指标详情（从图谱库查询）.

    Args:
        metric_id: 指标ID（通常是 code）
        request: FastAPI Request 对象

    Returns:
        指标详情
    """
    try:
        _, _, graph_store = get_services_from_request(request)

        if not graph_store:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="图谱服务未初始化"
            )

        # 从图谱查询指标节点
        metric_node = graph_store.get_metric_node(metric_id)
        if not metric_node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"指标 {metric_id} 不存在"
            )

        # 构建响应
        return {
            "metric_id": metric_id,
            "name": metric_node.name,
            "code": metric_node.code,
            "description": metric_node.description,
            "domain": metric_node.domain,
            "synonyms": metric_node.synonyms,
            "formula": metric_node.formula,
            "importance": metric_node.importance
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询指标失败: {e}"
        ) from e


@router.post("/metrics/{metric_id}/summary")
async def regenerate_metric_summary(
    metric_id: str,
    use_llm: bool = True,
    request: Request = None
):
    """重新生成指标摘要.

    Args:
        metric_id: 指标ID
        use_llm: 是否使用GLM生成
        request: FastAPI Request 对象

    Returns:
        新的摘要
    """
    try:
        if not use_llm:
            return {"message": "LLM摘要生成未启用"}

        _, _, graph_store = get_services_from_request(request)

        if not graph_store:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="图谱服务未初始化"
            )

        # 从图谱库查询指标元数据
        metric_node = graph_store.get_metric_node(metric_id)
        if not metric_node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"指标 {metric_id} 不存在"
            )

        metric_data = {
            "name": metric_node.name,
            "code": metric_node.code,
            "description": metric_node.description,
            "domain": metric_node.domain,
            "synonyms": metric_node.synonyms,
            "formula": metric_node.formula
        }

        summary_service = get_summary_service()
        if not summary_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GLM 摘要服务未配置"
            )

        summary = await summary_service.generate_metric_summaries(metric_data)

        return {
            "metric_id": metric_id,
            "summary": summary,
            "regenerated_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新生成摘要失败: {e}"
        ) from e


@router.get("/tasks/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """获取异步任务状态.

    Args:
        task_id: 任务ID

    Returns:
        任务状态
    """
    if task_id not in _tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_id}"
        )

    return _tasks[task_id]


@router.get("/health")
async def management_health_check(request: Request):
    """健康检查."""
    try:
        vector_store, neo4j_client, _ = get_services_from_request(request)
    except HTTPException:
        vector_store, neo4j_client = None, None

    summary_service = get_summary_service()

    return {
        "status": "healthy",
        "service": "data-management",
        "features": {
            "glm_summary": summary_service is not None,
            "neo4j": neo4j_client is not None,
            "qdrant": vector_store is not None
        },
        "config": {
            "zhipuai_model": settings.zhipuai.model if settings.zhipuai.api_key else None,
            "zhipuai_batch_size": settings.zhipuai.batch_size
        }
    }
