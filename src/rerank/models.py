"""精排层特征定义."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class QueryContext:
    """查询上下文.

    Attributes:
        query: 原始查询文本
        query_tokens: 查询分词
        query_domain: 查询的业务域（可选）
    """

    query: str
    query_tokens: list[str]
    query_domain: Optional[str] = None

    @classmethod
    def from_text(cls, query: str, domain: Optional[str] = None) -> "QueryContext":
        """从查询文本创建上下文.

        Args:
            query: 查询文本
            domain: 业务域

        Returns:
            查询上下文
        """
        # 简单分词（按空格和中文标点）
        import re

        tokens = re.findall(r"[\w]+", query)
        return cls(query=query, query_tokens=tokens, query_domain=domain)


@dataclass
class Candidate:
    """候选指标.

    Attributes:
        metric_id: 指标ID
        name: 指标名称
        code: 指标编码
        description: 业务含义
        domain: 业务域
        synonyms: 同义词列表
        importance: 重要性
        formula: 计算公式
        vector_score: 向量召回分数
        graph_score: 图谱召回分数
        source: 召回来源
    """

    metric_id: str
    name: str
    code: str
    description: str
    domain: str
    synonyms: list[str]
    importance: float
    formula: Optional[str]
    vector_score: float
    graph_score: float
    source: str

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "domain": self.domain,
            "synonyms": self.synonyms,
            "importance": self.importance,
            "formula": self.formula,
            "vector_score": self.vector_score,
            "graph_score": self.graph_score,
            "source": self.source,
        }


@dataclass
class FeatureVector:
    """特征向量.

    Attributes:
        features: 特征字典（特征名 -> 特征值）
    """

    features: dict[str, float]

    def get(self, name: str, default: float = 0.0) -> float:
        """获取特征值.

        Args:
            name: 特征名
            default: 默认值

        Returns:
            特征值
        """
        return self.features.get(name, default)

    def set(self, name: str, value: float) -> None:
        """设置特征值.

        Args:
            name: 特征名
            value: 特征值
        """
        self.features[name] = value
