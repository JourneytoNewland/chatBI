"""生产级意图识别服务器（集成智谱AI）."""

import os
import sys
sys.path.insert(0, "/Users/wangzheng/Downloads/playDemo/AntigravityDemo/chatBI")

from datetime import datetime
from typing import Any, Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# 导入增强版混合识别器
from src.inference.enhanced_hybrid import EnhancedHybridIntentRecognizer
from src.inference.intent import QueryIntent
from src.recall.semantic_recall import FallbackSemanticRecall

app = FastAPI(
    title="智能问数系统 - 生产版",
    version="2.0",
    description="基于智谱AI + BGE-M3的企业级意图识别系统"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化混合识别器（使用智谱AI）
print("\n🚀 初始化意图识别系统...")
print("=" * 60)

recognizer = EnhancedHybridIntentRecognizer(
    llm_provider="zhipu",  # 使用智谱AI
    enable_semantic=True   # 启用语义向量检索
)

print(f"✅ 混合识别器初始化完成")
print(f"   LLM提供商: 智谱AI (GLM-4-Flash)")
print(f"   语义检索: 启用")
print(f"   架构: 三层混合 (规则 → 语义 → LLM)")
print("=" * 60 + "\n")

# 模拟指标数据
MOCK_METRICS = [
    {
        "metric_id": "m001",
        "name": "GMV",
        "code": "gmv",
        "description": "成交总额（Gross Merchandise Volume）",
        "domain": "电商",
        "synonyms": ["成交金额", "交易额", "成交总额", "销售额"],
        "formula": "SUM(order_amount)",
    },
    {
        "metric_id": "m002",
        "name": "DAU",
        "code": "dau",
        "description": "日活跃用户数（Daily Active Users）",
        "domain": "用户",
        "synonyms": ["日活", "日活跃用户", "每日活跃用户"],
        "formula": "COUNT(active_users WHERE date = current_date)",
    },
    {
        "metric_id": "m003",
        "name": "MAU",
        "code": "mau",
        "description": "月活跃用户数（Monthly Active Users）",
        "domain": "用户",
        "synonyms": ["月活", "月活跃用户", "每月活跃用户"],
        "formula": "COUNT(active_users WHERE month = current_month)",
    },
    {
        "metric_id": "m004",
        "name": "ARPU",
        "code": "arpu",
        "description": "平均每用户收入（Average Revenue Per User）",
        "domain": "营收",
        "synonyms": ["人均收入", "每用户平均收入"],
        "formula": "SUM(revenue) / COUNT(users)",
    },
    {
        "metric_id": "m005",
        "name": "转化率",
        "code": "conversion_rate",
        "description": "访客转化为用户的比例",
        "domain": "营销",
        "synonyms": ["转化比率", "访问转化率"],
        "formula": "COUNT(conversions) / COUNT(visitors)",
    },
]

# 请求/响应模型
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="查询文本")
    top_k: int = Field(default=10, ge=1, le=100, description="返回结果数量")


class MetricCandidate(BaseModel):
    metric_id: str
    name: str
    code: str
    description: str
    domain: str
    score: float
    synonyms: List[str]
    formula: Optional[str]


class SearchResponse(BaseModel):
    query: str
    intent: dict
    candidates: List[MetricCandidate]
    total: int
    source_layer: str
    latency_ms: float


@app.get("/")
async def root():
    """根路径."""
    return {
        "service": "智能问数系统",
        "version": "2.0 (Production)",
        "features": {
            "llm_provider": "智谱AI GLM-4-Flash",
            "architecture": "三层混合架构",
            "semantic_search": "BGE-M3 + Qdrant",
            "intent_dimensions": "7维识别"
        },
        "docs": "/docs",
        "visualization": "打开 frontend/intent-visualization.html"
    }


@app.get("/health")
async def health_check():
    """健康检查."""
    return {
        "status": "healthy",
        "service": "intent-recognition-production",
        "llm_provider": "zhipu",
        "model": "glm-4-flash"
    }


@app.post("/api/v1/search", response_model=SearchResponse)
async def search_metrics(request: SearchRequest) -> SearchResponse:
    """智能检索指标（三层混合架构）."""

    import time
    start = time.time()

    # 1. 意图识别（三层混合）
    result = recognizer.recognize(request.query, top_k=request.top_k)

    # 2. 使用核心查询进行匹配
    core_query = result.final_intent.core_query or request.query
    core_query = core_query.strip()

    # 3. 指标匹配
    candidates = []
    for metric in MOCK_METRICS:
        score = calculate_similarity(core_query, metric)
        if score > 0:
            candidates.append({**metric, "score": score})

    candidates.sort(key=lambda x: x["score"], reverse=True)
    candidates = candidates[:request.top_k]

    # 4. 格式化结果
    formatted_candidates = [
        MetricCandidate(
            metric_id=c["metric_id"],
            name=c["name"],
            code=c["code"],
            description=c["description"],
            domain=c["domain"],
            score=c["score"],
            synonyms=c["synonyms"],
            formula=c.get("formula")
        )
        for c in candidates
    ]

    # 5. 格式化意图
    intent = {
        "core_query": result.final_intent.core_query,
        "time_range": format_time_range(result.final_intent.time_range),
        "time_granularity": format_enum(result.final_intent.time_granularity),
        "aggregation_type": format_enum(result.final_intent.aggregation_type),
        "dimensions": result.final_intent.dimensions,
        "comparison_type": result.final_intent.comparison_type,
        "filters": result.final_intent.filters
    }

    latency = time.time() - start

    return SearchResponse(
        query=request.query,
        intent=intent,
        candidates=formatted_candidates,
        total=len(formatted_candidates),
        source_layer=result.source_layer,
        latency_ms=round(latency * 1000, 2)
    )


@app.post("/api/v1/debug/intent-visualization")
async def debug_intent_visualization(request: SearchRequest):
    """意图识别可视化调试接口."""

    import time
    start = time.time()

    # 执行混合识别
    result = recognizer.recognize(request.query, top_k=request.top_k)

    # 构建可视化数据
    return {
        "query_info": {
            "original_query": request.query,
            "query_length": len(request.query),
            "core_query": result.final_intent.core_query
        },

        "recognition_timeline": [
            {
                "layer": layer.layer_name,
                "success": layer.success,
                "confidence": layer.confidence,
                "duration_ms": round(layer.duration * 1000, 2),
                "metadata": layer.metadata
            }
            for layer in result.all_layers
        ],

        "final_intent": {
            "core_query": result.final_intent.core_query,
            "time_range": format_time_range(result.final_intent.time_range),
            "time_granularity": format_enum(result.final_intent.time_granularity),
            "aggregation_type": format_enum(result.final_intent.aggregation_type),
            "dimensions": result.final_intent.dimensions,
            "comparison_type": result.final_intent.comparison_type,
            "filters": result.final_intent.filters
        },

        "performance": {
            "total_duration_ms": round(result.total_duration * 1000, 2),
            "source_layer": result.source_layer,
            "layer_breakdown": {
                layer.layer_name: round(layer.duration * 1000, 2)
                for layer in result.all_layers
            }
        },

        "confidence_heatmap": [
            {
                "layer": layer.layer_name,
                "confidence": layer.confidence,
                "status": "✓" if layer.success else "✗"
            }
            for layer in result.all_layers
        ],

        "llm_reasoning": extract_llm_reasoning(result)
    }


@app.get("/api/v1/statistics")
async def get_statistics():
    """获取系统统计信息."""
    return recognizer.get_statistics()


# 辅助函数
def calculate_similarity(query: str, metric: dict) -> float:
    """计算查询与指标的相似度."""
    import re
    query_clean = re.sub(r'^[的的之之]+', '', query.lower().strip())
    query_clean = re.sub(r'[的的之之]+$', '', query_clean)

    if query_clean == metric["name"].lower():
        return 1.0
    elif any(query_clean == syn.lower() for syn in metric["synonyms"]):
        return 0.98
    elif query_clean in metric["name"].lower():
        return 0.85
    elif query_clean in metric["description"].lower():
        return 0.75
    elif any(query_clean in syn.lower() for syn in metric["synonyms"]):
        return 0.80
    return 0.0


def format_time_range(time_range: Optional[tuple]) -> Optional[dict]:
    """格式化时间范围."""
    if not time_range:
        return None
    start, end = time_range
    return {
        "start": start.strftime("%Y-%m-%d") if hasattr(start, "strftime") else str(start),
        "end": end.strftime("%Y-%m-%d") if hasattr(end, "strftime") else str(end)
    }


def format_enum(value) -> Optional[str]:
    """格式化枚举值."""
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def extract_llm_reasoning(result) -> Optional[dict]:
    """提取LLM推理过程."""
    for layer in result.all_layers:
        if "LLM" in layer.layer_name and layer.metadata.get("reasoning"):
            return {
                "model": layer.metadata.get("model"),
                "reasoning": layer.metadata.get("reasoning"),
                "tokens_used": layer.metadata.get("tokens_used"),
                "cost": layer.metadata.get("cost")
            }
    return None


if __name__ == "__main__":
    print("\n🎯 智能问数系统 v2.0 - 生产版")
    print("=" * 60)
    print("服务地址: http://localhost:8000")
    print("API 文档: http://localhost:8000/docs")
    print("可视化界面: 打开 frontend/intent-visualization.html")
    print("=" * 60)
    print("\n核心特性:")
    print("  ✅ 智谱AI GLM-4 Flash (¥1/1M tokens)")
    print("  ✅ 三层混合架构 (规则 → 语义 → LLM)")
    print("  ✅ 7维意图识别 (时间/聚合/维度/比较/过滤)")
    print("  ✅ 实时可视化调试")
    print("  ✅ 10+ 模拟指标数据")
    print("\n按 Ctrl+C 停止服务\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
