"""演示服务器 - 使用模拟数据测试意图识别和前端."""

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.inference.intent import IntentRecognizer

# 创建 FastAPI 应用
app = FastAPI(
    title="智能问数系统 - 演示模式",
    description="使用模拟数据测试意图识别和前端界面",
    version="1.0.0-demo",
)

# 添加 CORS 支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 意图识别器
intent_recognizer = IntentRecognizer()

# 模拟指标数据
MOCK_METRICS = [
    {
        "metric_id": "m001",
        "name": "GMV",
        "code": "gmv",
        "description": "成交总额（Gross Merchandise Volume）",
        "domain": "电商",
        "score": 0.95,
        "synonyms": ["成交金额", "交易额", "成交总额"],
        "formula": "SUM(order_amount)",
    },
    {
        "metric_id": "m002",
        "name": "DAU",
        "code": "dau",
        "description": "日活跃用户数（Daily Active Users）",
        "domain": "用户",
        "score": 0.90,
        "synonyms": ["日活", "日活跃用户"],
        "formula": "COUNT(active_users)",
    },
    {
        "metric_id": "m003",
        "name": "MAU",
        "code": "mau",
        "description": "月活跃用户数（Monthly Active Users）",
        "domain": "用户",
        "score": 0.85,
        "synonyms": ["月活", "月活跃用户"],
        "formula": "COUNT(active_users WHERE month = current_month)",
    },
    {
        "metric_id": "m004",
        "name": "ARPU",
        "code": "arpu",
        "description": "平均每用户收入（Average Revenue Per User）",
        "domain": "营收",
        "score": 0.80,
        "synonyms": ["人均收入", "每用户平均收入"],
        "formula": "total_revenue / active_users",
    },
    {
        "metric_id": "m005",
        "name": "转化率",
        "code": "conversion_rate",
        "description": "用户转化率",
        "domain": "电商",
        "score": 0.75,
        "synonyms": ["转化率", "转化比率"],
        "formula": "conversions / visitors * 100",
    },
    {
        "metric_id": "m006",
        "name": "客单价",
        "code": "avg_order_value",
        "description": "平均订单金额",
        "domain": "电商",
        "score": 0.70,
        "synonyms": ["平均客单价", "平均订单金额"],
        "formula": "SUM(order_amount) / COUNT(orders)",
    },
    {
        "metric_id": "m007",
        "name": "LTV",
        "code": "ltv",
        "description": "用户生命周期价值（Lifetime Value）",
        "domain": "营收",
        "score": 0.65,
        "synonyms": ["生命周期价值", "用户价值"],
        "formula": "ARPU * lifespan",
    },
    {
        "metric_id": "m008",
        "name": "留存率",
        "code": "retention_rate",
        "description": "用户留存率",
        "domain": "用户",
        "score": 0.60,
        "synonyms": ["留存率", "用户留存"],
        "formula": "retained_users / total_users * 100",
    },
    {
        "metric_id": "m009",
        "name": "ROI",
        "code": "roi",
        "description": "投资回报率（Return on Investment）",
        "domain": "营销",
        "score": 0.55,
        "synonyms": ["投资回报率", "回报率"],
        "formula": "(revenue - cost) / cost * 100",
    },
    {
        "metric_id": "m010",
        "name": "CTR",
        "code": "ctr",
        "description": "点击率（Click-Through Rate）",
        "domain": "营销",
        "score": 0.50,
        "synonyms": ["点击率", "点击比率"],
        "formula": "clicks / impressions * 100",
    },
]


class IntentInfo(BaseModel):
    """意图识别信息."""

    core_query: str = Field(..., description="核心查询词")
    time_range: Optional[tuple[datetime, datetime]] = Field(None, description="时间范围")
    time_granularity: Optional[str] = Field(None, description="时间粒度")
    aggregation_type: Optional[str] = Field(None, description="聚合类型")
    dimensions: list[str] = Field(default_factory=list, description="维度列表")
    comparison_type: Optional[str] = Field(None, description="比较类型")
    filters: dict[str, Any] = Field(default_factory=dict, description="过滤条件")


class MetricCandidate(BaseModel):
    """指标候选结果."""

    metric_id: str = Field(..., description="指标ID")
    name: str = Field(..., description="指标名称")
    code: str = Field(..., description="指标编码")
    description: str = Field(..., description="业务含义")
    domain: str = Field(..., description="业务域")
    score: float = Field(..., description="相似度分数")
    synonyms: list[str] = Field(default_factory=list, description="同义词列表")
    formula: Optional[str] = Field(None, description="计算公式")


class SearchRequest(BaseModel):
    """检索请求."""

    query: str = Field(..., min_length=1, max_length=500, description="查询文本")
    top_k: int = Field(default=10, ge=1, le=100, description="返回结果数量")
    score_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="相似度阈值",
    )


class SearchResponse(BaseModel):
    """检索响应."""

    query: str
    intent: Optional[IntentInfo] = None
    candidates: list[MetricCandidate]
    total: int
    execution_time: float


def simple_match(query: str, metrics: list) -> list:
    """简单的匹配算法（模拟向量检索）."""
    query_lower = query.lower()
    results = []

    for metric in metrics:
        score = 0.0

        # 精确匹配
        if query_lower == metric["name"].lower():
            score = 1.0
        # 同义词匹配
        elif any(query_lower == syn.lower() for syn in metric["synonyms"]):
            score = 0.95
        # 部分匹配
        elif query_lower in metric["name"].lower():
            score = 0.8
        elif query_lower in metric["description"].lower():
            score = 0.7
        elif any(query_lower in syn.lower() for syn in metric["synonyms"]):
            score = 0.75
        # 包含关系
        elif metric["name"].lower() in query_lower:
            score = 0.6

        if score > 0:
            results.append({**metric, "score": score})

    # 排序
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


@app.get("/")
async def root():
    """根路径."""
    return {
        "message": "智能问数系统 - 演示模式",
        "version": "1.0.0-demo",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """健康检查."""
    return {"status": "healthy", "mode": "demo"}


@app.post("/api/v1/search", response_model=SearchResponse)
async def search_metrics(request: SearchRequest) -> SearchResponse:
    """智能检索指标（演示模式）."""
    start_time = time.time()

    try:
        # 1. 意图识别
        intent = intent_recognizer.recognize(request.query)

        # 2. 使用核心查询进行匹配
        core_query = intent.core_query if intent.core_query else request.query
        matched_results = simple_match(core_query, MOCK_METRICS)

        # 3. 过滤阈值
        if request.score_threshold:
            matched_results = [
                r for r in matched_results if r["score"] >= request.score_threshold
            ]

        # 4. Top-K 截断
        matched_results = matched_results[: request.top_k]

        # 5. 格式化结果
        candidates = [
            MetricCandidate(
                metric_id=r["metric_id"],
                name=r["name"],
                code=r["code"],
                description=r["description"],
                domain=r["domain"],
                score=r["score"],
                synonyms=r["synonyms"],
                formula=r.get("formula"),
            )
            for r in matched_results
        ]

        # 6. 格式化意图信息
        intent_info = IntentInfo(
            core_query=intent.core_query,
            time_range=intent.time_range,
            time_granularity=intent.time_granularity.value if intent.time_granularity else None,
            aggregation_type=intent.aggregation_type.value if intent.aggregation_type else None,
            dimensions=intent.dimensions,
            comparison_type=intent.comparison_type,
            filters=intent.filters,
        )

        execution_time = (time.time() - start_time) * 1000

        return SearchResponse(
            query=request.query,
            intent=intent_info,
            candidates=candidates,
            total=len(candidates),
            execution_time=round(execution_time, 2),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败: {e}")


if __name__ == "__main__":
    import uvicorn

    print("""
    🚀 智能问数系统 - 演示模式
    =====================================
    服务地址: http://localhost:8000
    API 文档: http://localhost:8000/docs
    前端界面: 在浏览器中打开 frontend/index.html
    =====================================
    """)

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
