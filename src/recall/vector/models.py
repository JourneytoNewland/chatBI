"""向量召回层的数据模型定义."""

from typing import Optional

from pydantic import BaseModel, Field


class MetricMetadata(BaseModel):
    """指标元数据模型.

    Attributes:
        name: 指标名称
        code: 指标编码
        description: 业务含义描述
        synonyms: 同义词列表
        domain: 业务域
        formula: 计算公式（可选）
    """

    name: str = Field(..., description="指标名称")
    code: str = Field(..., description="指标编码")
    description: str = Field(..., description="业务含义描述")
    synonyms: list[str] = Field(default_factory=list, description="同义词列表")
    domain: str = Field(..., description="业务域")
    formula: Optional[str] = Field(None, description="计算公式")


class VectorizedMetric(BaseModel):
    """向量化后的指标模型.

    Attributes:
        metric_id: 指标唯一标识
        metadata: 指标元数据
        embedding: 768维向量
    """

    metric_id: str = Field(..., description="指标唯一标识")
    metadata: MetricMetadata = Field(..., description="指标元数据")
    embedding: list[float] = Field(..., description="768维向量")
