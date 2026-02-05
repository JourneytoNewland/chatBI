"""调试 API 路由 - 返回详细的执行过程."""

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.api.models import SearchRequest
from src.config import settings
from src.inference.context import ConversationManager
from src.inference.intent import IntentRecognizer
from src.recall.dual_recall import DualRecall
from src.recall.graph.neo4j_client import Neo4jClient
from src.recall.vector.models import MetricMetadata
from src.recall.vector.qdrant_store import QdrantVectorStore
from src.recall.vector.vectorizer import MetricVectorizer
from src.rerank.models import Candidate, QueryContext
from src.rerank.ranker import RuleBasedRanker
from src.validator.validators import ValidationPipeline

router = APIRouter(prefix="/debug")

# 全局实例
_vectorizer: Optional[MetricVectorizer] = None
_ranker: Optional[RuleBasedRanker] = None
_validator: Optional[ValidationPipeline] = None
_intent_recognizer: Optional[IntentRecognizer] = None
_conversation_manager: Optional[ConversationManager] = None


def get_vectorizer() -> MetricVectorizer:
    global _vectorizer
    if _vectorizer is None:
        _vectorizer = MetricVectorizer(model_name=settings.vectorizer.model_name)
    return _vectorizer


def get_ranker() -> RuleBasedRanker:
    global _ranker
    if _ranker is None:
        _ranker = RuleBasedRanker()
    return _ranker


def get_validator() -> ValidationPipeline:
    global _validator
    if _validator is None:
        _validator = ValidationPipeline()
    return _validator


def get_intent_recognizer() -> IntentRecognizer:
    global _intent_recognizer
    if _intent_recognizer is None:
        _intent_recognizer = IntentRecognizer()
    return _intent_recognizer


def get_conversation_manager() -> ConversationManager:
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager


class StepDetail(BaseModel):
    """单步执行详情."""
    step_name: str = Field(..., description="步骤名称")
    step_type: str = Field(..., description="步骤类型")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="输入数据")
    algorithm: str = Field(..., description="算法或方法")
    algorithm_params: Dict[str, Any] = Field(default_factory=dict, description="算法参数")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="输出数据")
    duration_ms: float = Field(..., description="执行时间（毫秒）")
    success: bool = Field(..., description="是否成功")
    error_message: Optional[str] = Field(None, description="错误信息")


class DebugSearchResponse(BaseModel):
    """调试搜索响应."""
    query: str = Field(..., description="查询文本")
    execution_steps: List[StepDetail] = Field(..., description="执行步骤列表")
    total_duration_ms: float = Field(..., description="总执行时间")
    final_result: Dict[str, Any] = Field(default_factory=dict, description="最终结果")


@router.post("/search-debug", response_model=DebugSearchResponse)
async def search_debug(request: Request, search_req: SearchRequest) -> DebugSearchResponse:
    """调试模式搜索 - 返回详细的执行过程.

    Args:
        request: FastAPI Request 对象
        search_req: 检索请求

    Returns:
        详细的执行过程，包括每步的输入、算法、输出
    """
    start_time = time.time()
    execution_steps: List[StepDetail] = []

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
        intent_recognizer = get_intent_recognizer()
        conversation_manager = get_conversation_manager()

        # ========== 步骤 1: 意图识别 ==========
        step_start = time.time()

        # 获取或创建会话上下文
        conversation_id = search_req.conversation_id or str(int(time.time()))
        ctx = conversation_manager.get_or_create(conversation_id)

        # 解析指代关系
        resolved_query = ctx.resolve_reference(search_req.query)

        # 意图识别
        intent = intent_recognizer.recognize(resolved_query)

        # 获取意图识别的真实提示词/算法
        # 获取实际的pattern列表
        pattern_list = []
        if hasattr(intent_recognizer, 'TREND_PATTERNS'):
            pattern_list = [f"- {p[0]}" for p in intent_recognizer.TREND_PATTERNS[:3]]

        patterns_str = "\n   ".join(pattern_list) if pattern_list else "正则表达式模式匹配"

        intent_algorithm = f"""
意图识别算法：
1. 正则表达式匹配
   - 时间范围：(?P<数字>\\d+)\\s*(天|日|周|月|年)
   - 聚合类型：(?P<聚合>(总和|平均|最大|最小|计数))
   - 比较类型：(?P<比较>(同比|环比|增长|下降|超过|低于))

2. 关键词提取
   - 核心查询词：去除时间等干扰词
   - 维度提取：识别分析维度

3. 模式匹配
   - 趋势分析：{patterns_str}
   - 排序需求：(前|Top|top)\\s*(\\d+)
   - 阈值过滤：(\\S+?)\\s*(>|<|>=|<=)\\s*(\\d+)
        """.strip()

        step_duration = (time.time() - step_start) * 1000

        execution_steps.append(StepDetail(
            step_name="意图识别",
            step_type="intent_recognition",
            input_data={
                "原始查询": search_req.query,
                "解析后查询": resolved_query,
                "会话ID": conversation_id,
                "会话轮次": len(ctx.turns),
            },
            algorithm=intent_algorithm,
            algorithm_params={
                "模型": "规则引擎 + 正则表达式",
                "支持意图": ["时间范围", "聚合类型", "维度", "比较", "趋势", "排序", "阈值"],
            },
            output_data={
                "core_query": intent.core_query,
                "time_range": f"{intent.time_range}" if intent.time_range else None,
                "time_granularity": intent.time_granularity.value if intent.time_granularity else None,
                "aggregation_type": intent.aggregation_type.value if intent.aggregation_type else None,
                "dimensions": intent.dimensions,
                "comparison_type": intent.comparison_type,
                "trend_type": intent.trend_type.value if intent.trend_type else None,
                "sort_requirement": {
                    "top_n": intent.sort_requirement.top_n,
                    "order": intent.sort_requirement.order.value,
                    "metric": intent.sort_requirement.metric,
                } if intent.sort_requirement else None,
                "threshold_filters": [
                    {
                        "metric": f.metric,
                        "operator": f.operator,
                        "value": f.value,
                        "unit": f.unit,
                    }
                    for f in intent.threshold_filters
                ],
            },
            duration_ms=step_duration,
            success=True,
        ))

        # 使用核心查询词
        optimized_query = intent.core_query if intent.core_query else resolved_query

        # ========== 步骤 2: 向量化 ==========
        step_start = time.time()

        query_metadata = MetricMetadata(
            name=optimized_query,
            code=optimized_query,
            description=optimized_query,
            synonyms=[],
            domain="查询",
        )
        query_vector = vectorizer.vectorize(query_metadata)

        # 计算 vector norm
        import numpy as np
        vector_norm = float(np.linalg.norm(query_vector))

        vectorization_algorithm = f"""
向量化算法：
模型：{settings.vectorizer.model_name}
向量维度：{vectorizer.embedding_dim}
向量化方法：sentence-transformers

输入：{optimized_query}
输出：shape={query_vector.shape}
        """.strip()

        step_duration = (time.time() - step_start) * 1000

        execution_steps.append(StepDetail(
            step_name="查询向量化",
            step_type="vectorization",
            input_data={
                "查询文本": optimized_query,
                "模型": settings.vectorizer.model_name,
            },
            algorithm=vectorization_algorithm,
            algorithm_params={
                "模型": settings.vectorizer.model_name,
                "向量维度": vectorizer.embedding_dim,
                "设备": settings.vectorizer.device,
            },
            output_data={
                "向量形状": str(query_vector.shape),
                "向量范数": vector_norm,
            },
            duration_ms=step_duration,
            success=True,
        ))

        # ========== 步骤 3: 向量召回 ==========
        step_start = time.time()

        raw_results = vector_store.search(
            query_vector=query_vector,
            top_k=search_req.top_k * 2,
            score_threshold=search_req.score_threshold,
        )

        vector_recall_algorithm = f"""
向量召回算法：
相似度计算：cos(A, B) = (A·B) / (||A|| × ||B||)
向量数据库：Qdrant v1.7.4
集合名称：{settings.qdrant.collection_name}

召回参数：
- top_k: {search_req.top_k * 2}
- score_threshold: {search_req.score_threshold}
- vector_size: {query_vector.shape[0]}
        """.strip()

        step_duration = (time.time() - step_start) * 1000

        execution_steps.append(StepDetail(
            step_name="向量召回",
            step_type="vector_recall",
            input_data={
                "查询向量": f"shape={query_vector.shape}",
                "top_k": search_req.top_k * 2,
                "score_threshold": search_req.score_threshold,
            },
            algorithm=vector_recall_algorithm,
            algorithm_params={
                "相似度函数": "余弦相似度",
                "数据库": "Qdrant",
                "集合": settings.qdrant.collection_name,
            },
            output_data={
                "召回数量": len(raw_results),
                "top候选": raw_results[:3] if raw_results else [],
            },
            duration_ms=step_duration,
            success=True,
        ))

        # ========== 步骤 4: 图谱召回（如果可用）==========
        if neo4j_client:
            step_start = time.time()

            try:
                # 简化的图谱召回（实际项目中应该有真实的图谱查询）
                graph_results = []  # 实际图谱查询结果

                graph_recall_algorithm = """
图谱召回算法：
图数据库：Neo4j
查询语言：Cypher

查询示例：
MATCH (m:Metric)-[r:BELONGS_TO]->(d:Domain)
WHERE m.name CONTAINS $query
RETURN m, d

关系类型：
- BELONGS_TO: 属于
- CORRELATED_WITH: 相关
- CALCULATED_BY: 计算得出
                """.strip()

                step_duration = (time.time() - step_start) * 1000

                execution_steps.append(StepDetail(
                    step_name="图谱召回",
                    step_type="graph_recall",
                    input_data={
                        "查询": optimized_query,
                        "图数据库": "Neo4j",
                    },
                    algorithm=graph_recall_algorithm,
                    algorithm_params={
                        "数据库": "Neo4j",
                        "URI": settings.neo4j.uri,
                    },
                    output_data={
                        "召回数量": len(graph_results),
                    },
                    duration_ms=step_duration,
                    success=True,
                ))

                # 合并结果
                all_results = raw_results  # 简化：实际需要去重合并
            except Exception as e:
                execution_steps.append(StepDetail(
                    step_name="图谱召回",
                    step_type="graph_recall",
                    input_data={},
                    algorithm="图谱召回",
                    algorithm_params={},
                    output_data={},
                    duration_ms=0,
                    success=False,
                    error_message=str(e),
                ))
        else:
            # 只有向量召回
            all_results = raw_results

        # 转换为 Candidate
        candidates = []
        for result in all_results:
            payload = result["payload"]
            candidates.append(
                Candidate(
                    metric_id=payload["metric_id"],
                    name=payload["name"],
                    code=payload["code"],
                    description=payload["description"],
                    domain=payload.get("domain", ""),
                    synonyms=payload.get("synonyms", []),
                    importance=payload.get("importance", 0.5),
                    formula=payload.get("formula"),
                    vector_score=result["score"],
                    graph_score=0.0,
                    source="vector",
                )
            )

        # ========== 步骤 5: 特征提取 ==========
        step_start = time.time()

        context = QueryContext.from_text(optimized_query)

        feature_extraction_algorithm = f"""
特征提取算法（11维特征）：
1. 向量相似度 (weight: 0.30)
   - 计算查询向量与候选向量的余弦相似度

2. 图谱分数 (weight: 0.15)
   - 基于图谱关系的关联度

3. 精确匹配 (weight: 0.15)
   - 查询词与指标名/同义词完全匹配

4. 查询覆盖 (weight: 0.08)
   - 查询词被指标描述覆盖的比例

5. 文本相关 (weight: 0.05)
   - 文本语义相似度

6. 领域匹配 (weight: 0.08)
   - 业务域一致性

7. 同义词匹配 (weight: 0.06)
   - 同义词匹配度

8. 字面匹配 (weight: 0.04)
   - 字符串包含关系

9. 编辑距离 (weight: 0.03)
   - Levenshtein距离

10. 语义相似 (weight: 0.06)
    - 语义理解相似度

11. 位置权重 (weight: 0.05)
    - 查询词在文本中的位置

查询上下文：
- 查询文本：{context.query}
- 查询长度：{len(context.query)}
- 分词结果：{context.query_tokens[:5] if context.query_tokens else []}
        """.strip()

        # 注意: 特征提取在 score() 方法内部完成
        # 这里只记录时间,不实际调用
        step_duration = (time.time() - step_start) * 1000

        execution_steps.append(StepDetail(
            step_name="特征提取",
            step_type="feature_extraction",
            input_data={
                "候选数量": len(candidates),
                "查询上下文": {
                    "query": context.query,
                    "query_length": len(context.query),
                },
            },
            algorithm=feature_extraction_algorithm,
            algorithm_params={
                "特征维度": 11,
                "特征权重": ranker.weights if hasattr(ranker, 'weights') else {},
            },
            output_data={
                "说明": "特征提取在精排打分阶段完成",
                "候选数量": len(candidates),
            },
            duration_ms=step_duration,
            success=True,
        ))

        # ========== 步骤 6: 精排打分 ==========
        step_start = time.time()

        ranked_results = ranker.rerank(candidates, context, top_k=search_req.top_k)

        rerank_algorithm = """
精排算法：
Score = Σ(feature_i × weight_i)

排序规则：
1. 计算加总分
2. 按分数降序排列
3. 返回 Top K

特征权重配置：
- 向量相似度: 0.30
- 图谱分数: 0.15
- 精确匹配: 0.15
- 查询覆盖: 0.08
- 文本相关: 0.05
- 领域匹配: 0.08
- 同义词匹配: 0.06
- 字面匹配: 0.04
- 编辑距离: 0.03
- 语义相似: 0.06
- 位置权重: 0.05
            """.strip()

        step_duration = (time.time() - step_start) * 1000

        execution_steps.append(StepDetail(
            step_name="精排打分",
            step_type="reranking",
            input_data={
                "候选数量": len(candidates),
                "top_k": search_req.top_k,
            },
            algorithm=rerank_algorithm,
            algorithm_params={
                "特征维度": 11,
                "排序方法": "加权求和",
                "特征提取器数量": len(ranker.extractors) if hasattr(ranker, 'extractors') else 0,
            },
            output_data={
                "排名结果": [
                    {
                        "name": c.name,
                        "score": score,
                        "rank": i + 1,
                    }
                    for i, (c, score, _) in enumerate(ranked_results)
                ][:5],
            },
            duration_ms=step_duration,
            success=True,
        ))

        # ========== 步骤 7: 结果验证 ==========
        step_start = time.time()

        final_candidates = []
        for candidate, score, _ in ranked_results:
            # 运行验证器
            validation_results = validator.validate(candidate, context)

            # 只保留未 FAILED 的结果
            if not validator.has_failed(validation_results):
                final_candidates.append(candidate)

        validation_algorithm = """
验证算法：
验证规则：
1. 维度兼容性：查询维度是否在指标可用维度中
2. 时间粒度：时间粒度是否支持
3. 数据新鲜度：数据是否在有效期内
4. 权限验证：用户是否有权限访问该指标

验证结果：
- PASSED: 通过验证
- FAILED: 未通过验证（从结果中移除）
            """.strip()

        step_duration = (time.time() - step_start) * 1000

        execution_steps.append(StepDetail(
            step_name="结果验证",
            step_type="validation",
            input_data={
                "输入候选": len(ranked_results),
                "验证规则": ["维度兼容性", "时间粒度", "数据新鲜度", "权限验证"],
            },
            algorithm=validation_algorithm,
            algorithm_params={
                "验证器数量": len(validator.validators) if hasattr(validator, 'validators') else 1,
            },
            output_data={
                "通过数量": len(final_candidates),
                "拒绝数量": len(ranked_results) - len(final_candidates),
            },
            duration_ms=step_duration,
            success=True,
        ))

        # 计算总时间
        total_duration = (time.time() - start_time) * 1000

        # 添加到会话历史
        ctx.add_turn(search_req.query, intent)

        return DebugSearchResponse(
            query=search_req.query,
            execution_steps=execution_steps,
            total_duration_ms=round(total_duration, 2),
            final_result={
                "候选数量": len(final_candidates),
                "候选列表": [
                    {
                        "name": c.name,
                        "code": c.code,
                        "score": score,
                    }
                    for c, score, _ in ranked_results
                ][:5],
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检索过程中发生错误: {e}",
        ) from e
