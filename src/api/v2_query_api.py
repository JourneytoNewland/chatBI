"""完整的智能问数API."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..inference.enhanced_hybrid import EnhancedHybridIntentRecognizer
from ..mql.generator import MQLGenerator
from ..mql.engine import MQLExecutionEngine
from ..mql.root_cause import RootCauseAnalyzer
from ..mql.intelligent_interpreter import IntelligentInterpreter
from ..mql.metrics import registry


router = APIRouter(prefix="/api/v2", tags=["intelligent-query"])

# 初始化组件
intent_recognizer = EnhancedHybridIntentRecognizer(llm_provider="zhipu")
mql_generator = MQLGenerator()
mql_engine = MQLExecutionEngine()
root_cause_analyzer = RootCauseAnalyzer()
intelligent_interpreter = IntelligentInterpreter(llm_model="glm-4-flash")


# 请求/响应模型
class QueryRequest(BaseModel):
    """问数请求."""
    query: str = Field(..., description="自然语言查询")
    top_k: int = Field(default=10, ge=1, le=100, description="返回结果数量")


class QueryResponse(BaseModel):
    """问数响应."""
    query: str
    intent: Dict[str, Any]
    mql: str
    result: Dict[str, Any]
    interpretation: Optional[Dict[str, Any]] = None  # 智能解读结果
    execution_time_ms: float


@router.get("/")
async def root():
    """根路径."""
    return {
        "service": "智能问数系统 v2.0",
        "features": [
            "自然语言查询",
            "7维意图识别",
            "MQL自动生成",
            "PostgreSQL真实数据",
            "智能解读（LLM）",
            "根因分析",
            "25+指标支持"
        ],
        "docs": "/docs"
    }


@router.get("/health")
async def health_check():
    """健康检查."""
    return {
        "status": "healthy",
        "service": "intelligent-query-v2",
        "metrics_count": len(registry.metrics)
    }


@router.post("/query", response_model=QueryResponse)
async def query_metrics(request: QueryRequest) -> QueryResponse:
    """智能问数主接口.

    流程:
    1. 意图识别（三层混合架构）
    2. MQL生成
    3. MQL执行（PostgreSQL）
    4. 智能解读（LLM）
    5. 结果返回
    """
    import time
    start = time.time()

    # 1. 意图识别
    intent_result = intent_recognizer.recognize(request.query)
    intent = intent_result.final_intent

    # 2. 生成MQL
    mql_query = mql_generator.generate(intent)

    # 3. 执行查询
    execution_result = mql_engine.execute(mql_query)

    # 4. 智能解读（新增）
    interpretation_dict = None
    if execution_result.get("result"):
        try:
            interpretation = intelligent_interpreter.interpret(
                query=request.query,
                mql_result=execution_result,
                metric_def=execution_result.get("metric", {})
            )
            interpretation_dict = interpretation.model_dump()
        except Exception as e:
            # 解读失败不影响主流程
            import logging
            logging.getLogger(__name__).warning(f"智能解读失败: {e}")
            interpretation_dict = None

    # 5. 格式化响应
    return QueryResponse(
        query=request.query,
        intent={
            "core_query": intent.core_query,
            "time_range": {
                "start": intent.time_range[0].strftime("%Y-%m-%d") if intent.time_range else None,
                "end": intent.time_range[1].strftime("%Y-%m-%d") if intent.time_range else None
            } if intent.time_range else None,
            "time_granularity": intent.time_granularity.value if intent.time_granularity else None,
            "aggregation_type": intent.aggregation_type.value if intent.aggregation_type else None,
            "dimensions": intent.dimensions,
            "comparison_type": intent.comparison_type,
            "filters": intent.filters
        },
        mql=str(mql_query),
        result=execution_result,
        interpretation=interpretation_dict,  # 新增智能解读结果
        execution_time_ms=time.time() - start
    )


@router.post("/analyze")
async def analyze_root_cause(request: QueryRequest):
    """根因分析接口."""
    # 1. 意图识别
    intent_result = intent_recognizer.recognize(request.query)
    intent = intent_result.final_intent

    # 2. 获取时间范围
    from ..mql.mql import TimeRange
    if intent.time_range:
        time_range = TimeRange(
            start=intent.time_range[0],
            end=intent.time_range[1],
            granularity=intent.time_granularity.value if intent.time_granularity else "day"
        )
    else:
        # 默认最近7天
        end = datetime.now()
        start = end - timedelta(days=7)
        time_range = TimeRange(start=start, end=end, granularity="day")

    # 3. 执行根因分析
    root_causes = root_cause_analyzer.analyze(
        metric=intent.core_query,
        time_range=time_range,
        dimensions=intent.dimensions
    )

    # 4. 格式化结果
    return {
        "query": request.query,
        "metric": intent.core_query,
        "time_range": {
            "start": time_range.start.strftime("%Y-%m-%d"),
            "end": time_range.end.strftime("%Y-%m-%d")
        },
        "root_causes": [
            {
                "type": cause.cause_type,
                "severity": cause.severity,
                "description": cause.description,
                "confidence": cause.confidence,
                "evidence": cause.evidence,
                "suggestions": cause.suggestions
            }
            for cause in root_causes
        ],
        "total_causes": len(root_causes)
    }


@router.get("/metrics")
async def list_metrics(
    domain: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50
):
    """查询指标列表."""
    if search:
        metrics = registry.search_metrics(search, limit=limit)
    elif domain:
        metrics = registry.get_metrics_by_domain(domain)
    elif category:
        metrics = registry.get_metrics_by_category(category)
    else:
        metrics = registry.get_all_metrics()

    return {
        "total": len(metrics),
        "metrics": metrics[:limit]
    }


@router.get("/metrics/{metric_id}")
async def get_metric_detail(metric_id: str):
    """获取指标详情."""
    metric = registry.get_metric(metric_id)

    if not metric:
        raise HTTPException(status_code=404, detail=f"指标不存在: {metric_id}")

    # 获取相关指标
    related = metric.get("related_metrics", [])

    return {
        **metric,
        "related_metrics_details": [
            registry.get_metric(m) for m in related if registry.get_metric(m)
        ]
    }


@router.get("/statistics")
async def get_statistics():
    """获取系统统计信息."""
    return {
        "intent_recognizer": intent_recognizer.get_statistics(),
        "metrics": {
            "total": len(registry.metrics),
            "by_domain": {
                domain: len(registry.get_metrics_by_domain(domain))
                for domain in ["电商", "用户", "营收", "营销", "客服", "增长"]
            },
            "by_category": {
                "交易": 3,
                "活跃度": 3,
                "增长": 3,
                "留存": 3,
                "价值": 2,
                "收入": 3,
                "盈利": 2,
                "效率": 2,
                "转化": 4,
                "复购": 1,
                "售后": 2,
                "体验": 1
            }
        },
        "capabilities": {
            "intent_dimensions": 7,
            "mql_operators": ["SELECT", "SUM", "AVG", "COUNT", "MAX", "MIN", "RATE", "RATIO"],
            "analysis_types": ["趋势分析", "维度下钻", "根因分析", "对比分析"],
            "supported_dimensions": ["地区", "品类", "渠道", "设备类型", "用户等级", "获客来源"]
        }
    }


# 添加到主API
from fastapi import FastAPI
from . import graph_endpoints

def create_app() -> FastAPI:
    """创建FastAPI应用."""
    app = FastAPI(
        title="智能问数系统 v2.0",
        description="基于MQL的企业级智能问数系统",
        version="2.0"
    )

    # 添加CORS中间件
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(router)
    app.include_router(graph_endpoints.router)

    return app


if __name__ == "__main__":
    import uvicorn

    app = create_app()

    print("\n🚀 智能问数系统 v2.0")
    print("=" * 60)
    print("服务地址: http://localhost:8000")
    print("API 文档: http://localhost:8000/docs")
    print("=" * 60)
    print("\n核心功能:")
    print("  ✅ 自然语言查询")
    print("  ✅ 7维意图识别")
    print("  ✅ MQL自动生成")
    print("  ✅ PostgreSQL真实数据")
    print("  ✅ 智能解读（LLM）")
    print("  ✅ 25+指标支持")
    print("  ✅ 根因分析")
    print("  ✅ 图谱管理")
    print("\n按 Ctrl+C 停止服务\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
