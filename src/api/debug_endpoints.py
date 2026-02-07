"""可视化调试API端点."""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..inference.hybrid_intent import HybridIntentRecognizer, HybridIntentResult

router = APIRouter(prefix="/api/v1/debug", tags=["debug"])

# 初始化混合识别器
hybrid_recognizer = HybridIntentRecognizer(
    enable_llm=True,
    enable_local_llm=False
)


class SearchRequest(BaseModel):
    """搜索请求."""
    query: str = Field(..., min_length=1, max_length=500, description="查询文本")
    top_k: int = Field(default=10, ge=1, le=100, description="返回结果数量")


@router.post("/intent-visualization")
async def visualize_intent_recognition(request: SearchRequest):
    """意图识别可视化接口.

    返回详细的识别过程，包括：
    - 每层的识别结果
    - 置信度变化
    - 耗时统计
    - 推理过程
    """

    # 执行混合识别
    result: HybridIntentResult = hybrid_recognizer.recognize(request.query)

    # 构建可视化数据
    visualization = {
        # 1. 查询信息
        "query_info": {
            "original_query": request.query,
            "query_length": len(request.query),
            "timestamp": datetime.now().isoformat()
        },

        # 2. 识别过程（时间线）
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

        # 3. 最终意图（7维卡片）
        "final_intent": {
            "core_query": result.final_intent.core_query,
            "time_range": _format_time_range(result.final_intent.time_range),
            "time_granularity": _format_granularity(result.final_intent.time_granularity),
            "aggregation_type": _format_aggregation(result.final_intent.aggregation_type),
            "dimensions": result.final_intent.dimensions,
            "comparison_type": result.final_intent.comparison_type,
            "filters": result.final_intent.filters,
        },

        # 4. 性能统计
        "performance": {
            "total_duration_ms": round(result.total_duration * 1000, 2),
            "source_layer": result.source_layer,
            "layer_breakdown": {
                layer.layer_name: round(layer.duration * 1000, 2)
                for layer in result.all_layers
            }
        },

        # 5. 置信度热力图
        "confidence_heatmap": [
            {
                "layer": layer.layer_name,
                "confidence": layer.confidence,
                "status": "✓" if layer.success else "✗"
            }
            for layer in result.all_layers
        ],

        # 6. LLM推理过程（如果使用了LLM）
        "llm_reasoning": None
    }

    # 提取LLM推理过程
    for layer in result.all_layers:
        if "LLM" in layer.layer_name and layer.metadata.get("reasoning"):
            visualization["llm_reasoning"] = {
                "model": layer.metadata.get("model"),
                "reasoning": layer.metadata.get("reasoning"),
                "cost": layer.metadata.get("cost")
            }

    return visualization


@router.get("/statistics")
async def get_recognition_statistics():
    """获取识别器统计信息.

    返回：
    - 总查询数
    - 各层命中率
    - 失败率
    - 成本估算
    """
    return hybrid_recognizer.get_statistics()


@router.post("/compare-methods")
async def compare_recognition_methods(request: SearchRequest):
    """对比不同识别方法的结果.

    同时使用规则、语义、LLM三种方法识别，并对比结果。
    """

    from ..inference.intent import IntentRecognizer

    # 规则方法
    rule_recognizer = IntentRecognizer()
    rule_start = datetime.now()
    rule_intent = rule_recognizer.recognize(request.query)
    rule_duration = (datetime.now() - rule_start).total_seconds()

    # LLM方法（如果可用）
    llm_intent = None
    llm_duration = 0
    if hybrid_recognizer.llm_recognizer:
        llm_start = datetime.now()
        llm_result = hybrid_recognizer.llm_recognizer.recognize(request.query)
        llm_duration = (datetime.now() - llm_start).total_seconds()

        if llm_result:
            from ..inference.intent import QueryIntent, TimeGranularity, AggregationType
            llm_intent = QueryIntent(
                query=request.query,
                core_query=llm_result.core_query,
                time_range=None,
                time_granularity=_parse_granularity(llm_result.time_granularity),
                aggregation_type=_parse_aggregation(llm_result.aggregation_type),
                dimensions=llm_result.dimensions,
                comparison_type=llm_result.comparison_type,
                filters=llm_result.filters
            )

    return {
        "query": request.query,
        "comparison": [
            {
                "method": "Rule-Based",
                "result": _format_intent(rule_intent),
                "duration_ms": round(rule_duration * 1000, 2),
                "confidence": 0.8  # 估算
            },
            {
                "method": "LLM",
                "result": _format_intent(llm_intent) if llm_intent else None,
                "duration_ms": round(llm_duration * 1000, 2),
                "confidence": 0.95 if llm_intent else 0
            }
        ]
    }


# 辅助函数
def _format_time_range(time_range: Optional[tuple]) -> Optional[dict]:
    """格式化时间范围."""
    if not time_range:
        return None
    start, end = time_range
    return {
        "start": start.strftime("%Y-%m-%d") if hasattr(start, "strftime") else str(start),
        "end": end.strftime("%Y-%m-%d") if hasattr(end, "strftime") else str(end)
    }


def _format_granularity(granularity) -> Optional[str]:
    """格式化时间粒度."""
    if granularity is None:
        return None
    return granularity.value if hasattr(granularity, "value") else str(granularity)


def _format_aggregation(aggregation) -> Optional[str]:
    """格式化聚合类型."""
    if aggregation is None:
        return None
    return aggregation.value if hasattr(aggregation, "value") else str(aggregation)


def _format_intent(intent) -> dict:
    """格式化意图对象."""
    if not intent:
        return {}
    return {
        "core_query": intent.core_query,
        "time_range": _format_time_range(intent.time_range),
        "time_granularity": _format_granularity(intent.time_granularity),
        "aggregation_type": _format_aggregation(intent.aggregation_type),
        "dimensions": intent.dimensions,
        "comparison_type": intent.comparison_type,
        "filters": intent.filters
    }


def _parse_granularity(value: Optional[str]):
    """解析时间粒度."""
    if not value:
        return None
    from ..inference.intent import TimeGranularity
    try:
        return TimeGranularity(value)
    except ValueError:
        return None


def _parse_aggregation(value: Optional[str]):
    """解析聚合类型."""
    if not value:
        return None
    from ..inference.intent import AggregationType
    try:
        return AggregationType(value)
    except ValueError:
        return None
