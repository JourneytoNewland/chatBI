"""Neo4j 图谱数据模型定义."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class MetricNode:
    """指标节点.

    Attributes:
        metric_id: 指标唯一标识
        name: 指标名称
        code: 指标编码
        description: 业务含义
        domain: 业务域
        importance: 重要性（0-1）
    """

    metric_id: str
    name: str
    code: str
    description: str
    domain: str
    importance: float = 0.5
    synonyms: list[str] = None
    formula: Optional[str] = None

    def __post_init__(self) -> None:
        """初始化后处理."""
        if self.synonyms is None:
            self.synonyms = []

    def to_cypher_props(self) -> dict[str, Any]:
        """转换为 Cypher 属性字典."""
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "domain": self.domain,
            "importance": self.importance,
            "synonyms": self.synonyms,
            "formula": self.formula,
        }


@dataclass
class DimensionNode:
    """维度节点.

    Attributes:
        dimension_id: 维度唯一标识
        name: 维度名称
        description: 维度描述
        values: 可能的取值列表
    """

    dimension_id: str
    name: str
    description: str
    values: list[str] = None

    def __post_init__(self) -> None:
        """初始化后处理."""
        if self.values is None:
            self.values = []

    def to_cypher_props(self) -> dict[str, Any]:
        """转换为 Cypher 属性字典."""
        return {
            "dimension_id": self.dimension_id,
            "name": self.name,
            "description": self.description,
            "values": self.values,
        }


@dataclass
class BusinessDomainNode:
    """业务域节点.

    Attributes:
        domain_id: 业务域唯一标识
        name: 业务域名称
        description: 业务域描述
    """

    domain_id: str
    name: str
    description: str

    def to_cypher_props(self) -> dict[str, Any]:
        """转换为 Cypher 属性字典."""
        return {
            "domain_id": self.domain_id,
            "name": self.name,
            "description": self.description,
        }


@dataclass
class BelongsToDomainRel:
    """指标属于业务域关系."""

    weight: float = 1.0


@dataclass
class HasDimensionRel:
    """指标拥有维度关系."""

    required: bool = True


@dataclass
class DerivedFromRel:
    """指标派生关系.

    Attributes:
        confidence: 置信度（0-1）
        formula: 派生公式
    """

    confidence: float = 0.8
    formula: Optional[str] = None


@dataclass
class CorrelatesWithRel:
    """指标相关性关系.

    Attributes:
        weight: 相关权重（0-1）
        correlation_type: 相关类型（positive/negative）
    """

    weight: float = 0.5
    correlation_type: str = "positive"  # positive | negative
