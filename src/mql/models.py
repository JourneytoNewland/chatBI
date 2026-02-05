"""MQL数据模型."""

from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional


class InterpretationResult(BaseModel):
    """智能解读结果.

    Attributes:
        summary: 总结（2-3句话）
        trend: 趋势（upward/downward/fluctuating/stable）
        key_findings: 关键发现（3-5点）
        insights: 深入洞察（2-3点）
        suggestions: 行动建议（2-3点）
        confidence: 置信度（0-1）
        data_analysis: 原始数据分析结果
    """

    summary: str
    trend: str
    key_findings: List[str]
    insights: List[str]
    suggestions: List[str]
    confidence: float
    data_analysis: Dict[str, Any]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "summary": "GMV呈显著上升趋势，7天内增长30%，平均每天增长4.3%。",
                "trend": "upward",
                "key_findings": [
                    "GMV从50万增长到65万，增长30%",
                    "平均每天增长4.3%，增速稳定",
                    "最低值48万，最高值65万"
                ],
                "insights": [
                    "增长趋势可能受促销活动影响",
                    "华东地区贡献最大，占比40%"
                ],
                "suggestions": [
                    "继续当前营销策略",
                    "关注华东地区客户需求变化"
                ],
                "confidence": 0.85,
                "data_analysis": {
                    "trend": "upward",
                    "change_rate": 30.0,
                    "volatility": 8.5,
                    "min": 480000,
                    "max": 650000,
                    "avg": 565000
                }
            }
        }
    )


class DataAnalysisResult(BaseModel):
    """数据分析结果.

    Attributes:
        trend: 趋势方向
        change_rate: 变化率（百分比）
        volatility: 波动性（标准差/均值 * 100）
        anomalies: 异常值索引列表
        min: 最小值
        max: 最大值
        avg: 平均值
        std: 标准差
    """

    trend: str
    change_rate: float
    volatility: float
    anomalies: List[int]
    min: float
    max: float
    avg: float
    std: Optional[float] = None


class MQLQueryResult(BaseModel):
    """MQL查询结果.

    Attributes:
        query: 原始查询字符串
        metric: 指标定义
        mql: MQL查询字符串
        result: 查询结果数据
        interpretation: 智能解读（可选）
        execution_time_ms: 执行时间（毫秒）
        row_count: 返回行数
    """

    query: str
    metric: Dict[str, Any]
    mql: str
    result: List[Dict[str, Any]]
    interpretation: Optional[InterpretationResult] = None
    execution_time_ms: int
    row_count: int
    sql: Optional[str] = None  # 调试用
