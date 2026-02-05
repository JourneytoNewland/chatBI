"""API 请求和响应模型."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class IntentInfo(BaseModel):
    """意图识别信息.

    Attributes:
        core_query: 核心查询词（去除时间等）
        time_range: 时间范围 (start_date, end_date)
        time_granularity: 时间粒度
        aggregation_type: 聚合类型
        dimensions: 维度列表
        comparison_type: 比较类型
        filters: 过滤条件
        trend_type: 趋势类型（新增）
        sort_requirement: 排序需求（新增）
        threshold_filters: 阈值过滤列表（新增）
    """

    # ========== 原有字段（保持不变） ==========
    core_query: str = Field(..., description="核心查询词")
    time_range: Optional[tuple[datetime, datetime]] = Field(None, description="时间范围")
    time_granularity: Optional[str] = Field(None, description="时间粒度")
    aggregation_type: Optional[str] = Field(None, description="聚合类型")
    dimensions: list[str] = Field(default_factory=list, description="维度列表")
    comparison_type: Optional[str] = Field(None, description="比较类型")
    filters: dict[str, Any] = Field(default_factory=dict, description="过滤条件")

    # ========== 新增字段（可选，默认None） ==========
    trend_type: Optional[str] = Field(None, description="趋势类型（upward/downward/fluctuating/stable）")
    sort_requirement: Optional[dict] = Field(None, description="排序需求（top_n, order, metric）")
    threshold_filters: list[dict] = Field(default_factory=list, description="阈值过滤列表")


class SearchRequest(BaseModel):
    """检索请求模型.

    Attributes:
        query: 查询文本
        top_k: 返回结果数量，默认 10
        score_threshold: 相似度阈值（可选）
        conversation_id: 会话ID（用于多轮对话，新增）
    """

    query: str = Field(..., min_length=1, max_length=500, description="查询文本")
    top_k: int = Field(default=10, ge=1, le=100, description="返回结果数量")
    score_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="相似度阈值，低于该值的结果将被过滤",
    )
    conversation_id: Optional[str] = Field(None, description="会话ID（用于多轮对话）")


class MetricCandidate(BaseModel):
    """指标候选结果.

    Attributes:
        metric_id: 指标ID
        name: 指标名称
        code: 指标编码
        description: 业务含义
        domain: 业务域
        score: 相似度分数
        synonyms: 同义词列表
        formula: 计算公式（可选）
    """

    metric_id: str = Field(..., description="指标ID")
    name: str = Field(..., description="指标名称")
    code: str = Field(..., description="指标编码")
    description: str = Field(..., description="业务含义")
    domain: str = Field(..., description="业务域")
    score: float = Field(..., description="相似度分数")
    synonyms: list[str] = Field(default_factory=list, description="同义词列表")
    formula: Optional[str] = Field(None, description="计算公式")


class SearchResponse(BaseModel):
    """检索响应模型.

    Attributes:
        query: 查询文本
        intent: 意图识别结果
        candidates: 候选指标列表
        total: 返回结果数量
        execution_time: 执行时间（毫秒）
        conversation_id: 会话ID（新增）
    """

    query: str = Field(..., description="查询文本")
    intent: Optional[IntentInfo] = Field(None, description="意图识别结果")
    candidates: list[MetricCandidate] = Field(..., description="候选指标列表")
    total: int = Field(..., description="返回结果数量")
    execution_time: float = Field(..., description="执行时间（毫秒）")
    conversation_id: Optional[str] = Field(None, description="会话ID")


class ErrorResponse(BaseModel):
    """错误响应模型.

    Attributes:
        error: 错误类型
        message: 错误信息
        detail: 详细信息（可选）
    """

    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误信息")
    detail: Optional[str] = Field(None, description="详细信息")
