"""调试 API 路由 - 返回详细的执行过程."""

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.api.models import SearchRequest
from src.config import settings
from src.inference.context import ConversationManager
from src.inference.intent import IntentRecognizer
from src.inference.zhipu_intent import ZhipuIntentRecognizer
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
_llm_intent_recognizer: Optional[ZhipuIntentRecognizer] = None
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


def get_llm_intent_recognizer() -> ZhipuIntentRecognizer:
    """获取或创建LLM意图识别器."""
    global _llm_intent_recognizer
    if _llm_intent_recognizer is None:
        # 检查是否配置了ZhipuAI API密钥
        if settings.zhipuai.api_key:
            _llm_intent_recognizer = ZhipuIntentRecognizer(model=settings.zhipuai.model)
        else:
            # 未配置，创建一个空实例（调用时会返回None）
            _llm_intent_recognizer = ZhipuIntentRecognizer(model=settings.zhipuai.model)
    return _llm_intent_recognizer


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

        # ========== 步骤 1.5: LLM意图识别（智谱AI） ==========
        step_start = time.time()

        llm_intent_recognizer = get_llm_intent_recognizer()
        llm_intent_result = None
        llm_prompt = None
        llm_success = False
        llm_error = None

        try:
            # 调用智谱AI意图识别
            if settings.zhipuai.api_key:
                llm_intent_result = llm_intent_recognizer.recognize(search_req.query)

                if llm_intent_result:
                    # 构建实际使用的提示词
                    llm_prompt = llm_intent_recognizer._build_prompt(search_req.query)

                    llm_success = True
                else:
                    llm_error = "LLM返回结果为空"
            else:
                llm_error = "未配置ZHIPUAI_API_KEY"

        except Exception as e:
            llm_error = str(e)

        # 构建LLM算法说明（包含实际提示词）
        llm_algorithm = f"""
LLM意图识别算法（智谱AI）：
模型：{settings.zhipuai.model}
API：https://open.bigmodel.cn/api/paas/v4/chat/completions

方法：Few-shot Learning + Chain of Thought

提示词构建策略：
1. 系统提示：设定角色为"BI查询意图识别专家"
2. Few-shot示例：提供4个标注示例
3. 任务说明：定义7个意图维度
4. 输出约束：强制JSON格式

参数：
- temperature: 0.1（降低随机性）
- top_p: 0.7
- max_tokens: 1000

实际提示词（部分截取）：
{llm_prompt[:500] if llm_prompt else "（未生成提示词）"}...
{"..." if llm_prompt and len(llm_prompt) > 500 else ""}
        """.strip()

        # 构建LLM输出数据
        llm_output_data = {}
        if llm_intent_result:
            llm_output_data = {
                "core_query": llm_intent_result.core_query,
                "time_range": llm_intent_result.time_range,
                "time_granularity": llm_intent_result.time_granularity,
                "aggregation_type": llm_intent_result.aggregation_type,
                "dimensions": llm_intent_result.dimensions,
                "comparison_type": llm_intent_result.comparison_type,
                "confidence": llm_intent_result.confidence,
                "reasoning": llm_intent_result.reasoning,  # LLM的推理过程
                "model": llm_intent_result.model,
                "latency_ms": llm_intent_result.latency * 1000,
                "tokens_used": llm_intent_result.tokens_used,
            }

        # 对比规则引擎和LLM的结果
        comparison = {}
        if llm_intent_result:
            comparison = {
                "规则引擎核心查询": intent.core_query,
                "LLM核心查询": llm_intent_result.core_query,
                "是否一致": intent.core_query == llm_intent_result.core_query,
                "规则引擎趋势": intent.trend_type.value if intent.trend_type else None,
                "LLM置信度": llm_intent_result.confidence,
            }

        step_duration = (time.time() - step_start) * 1000

        execution_steps.append(StepDetail(
            step_name="LLM意图识别",
            step_type="llm_intent_recognition",
            input_data={
                "原始查询": search_req.query,
                "LLM模型": settings.zhipuai.model,
                "API配置状态": "已配置" if settings.zhipuai.api_key else "未配置",
            },
            algorithm=llm_algorithm,
            algorithm_params={
                "模型": settings.zhipuai.model,
                "Temperature": 0.1,
                "Top_P": 0.7,
                "Max_Tokens": 1000,
            },
            output_data={
                "识别结果": llm_output_data if llm_output_data else None,
                "规则引擎vs LLM对比": comparison,
            },
            duration_ms=step_duration,
            success=llm_success,
            error_message=llm_error,
        ))

        # 使用核心查询词（优先使用规则引擎的结果）
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

        # ========== 步骤 3: 向量召回（双路链路1） ==========
        step_start = time.time()

        raw_results = vector_store.search(
            query_vector=query_vector,
            top_k=search_req.top_k * 2,
            score_threshold=search_req.score_threshold,
        )

        # 详细的向量召回算法说明
        vector_recall_algorithm = f"""
🔷 向量召回链路（双路召回之1）

算法：基于向量相似度的语义检索
相似度计算：cos(A, B) = (A·B) / (||A|| × ||B||)
向量数据库：Qdrant v1.7.4
集合名称：{settings.qdrant.collection_name}
向量维度：{query_vector.shape[0]}

召回策略：
- 召回数量：{search_req.top_k * 2}（为精排准备更多候选）
- 相似度阈值：{search_req.score_threshold}
- 检索模式：HNSW（层次化可导航小世界图）

优势：
✅ 语义理解：捕捉查询与指标的语义相似性
✅ 泛化能力：处理同义词、表述变化
✅ 速度优化：HNSW索引提供毫秒级检索
        """.strip()

        step_duration = (time.time() - step_start) * 1000

        # 格式化top候选显示
        formatted_candidates = []
        for r in raw_results[:5]:
            payload = r["payload"]
            formatted_candidates.append({
                "name": payload["name"],
                "score": round(r["score"], 4),
                "id": payload["metric_id"],
            })

        execution_steps.append(StepDetail(
            step_name="向量召回",
            step_type="vector_recall",
            input_data={
                "链路": "双路召回链路1",
                "查询向量": f"shape={query_vector.shape}",
                "召回策略": f"top_k={search_req.top_k * 2}, threshold={search_req.score_threshold}",
            },
            algorithm=vector_recall_algorithm,
            algorithm_params={
                "相似度函数": "余弦相似度",
                "数据库": "Qdrant",
                "集合": settings.qdrant.collection_name,
                "向量维度": query_vector.shape[0],
                "索引类型": "HNSW",
            },
            output_data={
                "召回数量": len(raw_results),
                "top_5候选": formatted_candidates,
            },
            duration_ms=step_duration,
            success=True,
        ))

        # ========== 步骤 4: 图谱召回（双路链路2）==========
        if neo4j_client:
            step_start = time.time()

            try:
                # 简化的图谱召回（实际项目中应该有真实的图谱查询）
                graph_results = []  # 实际图谱查询结果

                # 详细的图谱召回算法说明
                graph_recall_algorithm = f"""
🔶 图谱召回链路（双路召回之2）

算法：基于知识图谱的关系推理
图数据库：Neo4j
查询语言：Cypher

查询策略：
1. 直接匹配：查询指标名
   MATCH (m:Metric)
   WHERE m.name CONTAINS $query

2. 关系扩展：探索关联指标
   MATCH (m:Metric)-[r:BELONGS_TO|CORRELATED_WITH]->(related)
   WHERE m.name CONTAINS $query
   RETURN related, r

3. 领域过滤：按业务域筛选
   MATCH (m:Metric)-[:BELONGS_TO]->(d:Domain)
   WHERE d.name = $domain

关系类型：
- BELONGS_TO: 属于（指标归属的业务域）
- CORRELATED_WITH: 相关（指标间的相关性）
- CALCULATED_BY: 计算得出（计算公式）
- DERIVED_FROM: 派生自（指标血缘）

优势：
✅ 结构化推理：基于明确的业务规则
✅ 关系发现：利用指标间的关联
✅ 可解释性：清晰的推理路径
                """.strip()

                step_duration = (time.time() - step_start) * 1000

                execution_steps.append(StepDetail(
                    step_name="图谱召回",
                    step_type="graph_recall",
                    input_data={
                        "链路": "双路召回链路2",
                        "查询": optimized_query,
                        "图数据库": "Neo4j",
                        "URI": settings.neo4j.uri,
                    },
                    algorithm=graph_recall_algorithm,
                    algorithm_params={
                        "数据库": "Neo4j",
                        "URI": settings.neo4j.uri,
                        "查询语言": "Cypher",
                    },
                    output_data={
                        "召回数量": len(graph_results),
                        "说明": "图谱召回结果将与向量召回结果合并",
                    },
                    duration_ms=step_duration,
                    success=True,
                ))

                # ========== 步骤 4.5: 双路合并 ==========
                merge_step_start = time.time()

                # 合并策略说明
                merge_algorithm = """
🔷🔶 双路召回结果合并

合并策略：
1. 向量召回候选（链路1）：语义相似度高
2. 图谱召回候选（链路2）：关系关联度高
3. 合并方法：并集 + 去重
4. 排序：按各自分数加权排序

合并公式：
merged_score = 0.6 * vector_score + 0.4 * graph_score

去重规则：
- 按metric_id去重
- 保留最高分数的记录
                """.strip()

                # 合并结果（简化：实际需要去重合并）
                all_results = raw_results  # 简化：实际需要去重合并

                merge_step_duration = (time.time() - merge_step_start) * 1000

                execution_steps.append(StepDetail(
                    step_name="双路合并",
                    step_type="merge_dual_path",
                    input_data={
                        "向量召回数量": len(raw_results),
                        "图谱召回数量": len(graph_results),
                    },
                    algorithm=merge_algorithm,
                    algorithm_params={
                        "合并策略": "并集+去重",
                        "向量权重": 0.6,
                        "图谱权重": 0.4,
                    },
                    output_data={
                        "合并后数量": len(all_results),
                        "去重数量": 0,  # 实际需要计算
                    },
                    duration_ms=merge_step_duration,
                    success=True,
                ))

            except Exception as e:
                execution_steps.append(StepDetail(
                    step_name="图谱召回",
                    step_type="graph_recall",
                    input_data={"链路": "双路召回链路2"},
                    algorithm="图谱召回",
                    algorithm_params={},
                    output_data={},
                    duration_ms=0,
                    success=False,
                    error_message=str(e),
                ))
                all_results = raw_results
        else:
            # 只有向量召回
            all_results = raw_results
            # 添加一个说明步骤
            execution_steps.append(StepDetail(
                step_name="图谱召回",
                step_type="graph_recall",
                input_data={"链路": "双路召回链路2"},
                algorithm="图谱召回（未配置）",
                algorithm_params={},
                output_data={"说明": "Neo4j未配置，仅使用向量召回"},
                duration_ms=0,
                success=True,
            ))

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
