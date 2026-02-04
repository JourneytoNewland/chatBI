"""精排层特征提取器."""

from abc import ABC, abstractmethod

from src.rerank.models import Candidate, FeatureVector, QueryContext


class FeatureExtractor(ABC):
    """特征提取器基类.

    所有特征提取器都应继承此类并实现 extract 方法。
    """

    @abstractmethod
    def extract(self, candidate: Candidate, context: QueryContext) -> float:
        """提取特征值.

        Args:
            candidate: 候选指标
            context: 查询上下文

        Returns:
            特征值
        """

    @property
    def name(self) -> str:
        """获取特征名称."""
        return self.__class__.__name__


# ==================== 基础特征 ====================


class VectorSimilarityExtractor(FeatureExtractor):
    """向量相似度特征."""

    def extract(self, candidate: Candidate, context: QueryContext) -> float:
        """提取向量相似度."""
        return candidate.vector_score


class GraphScoreExtractor(FeatureExtractor):
    """图谱召回分数特征."""

    def extract(self, candidate: Candidate, context: QueryContext) -> float:
        """提取图谱分数."""
        return candidate.graph_score


class ImportanceExtractor(FeatureExtractor):
    """指标重要性特征."""

    def extract(self, candidate: Candidate, context: QueryContext) -> float:
        """提取重要性."""
        return candidate.importance


# ==================== 文本匹配特征 ====================


class QueryCoverageExtractor(FeatureExtractor):
    """查询词覆盖率特征."""

    def extract(self, candidate: Candidate, context: QueryContext) -> float:
        """计算查询词覆盖率."""
        if not context.query_tokens:
            return 0.0

        # 将候选指标信息合并为文本
        candidate_text = f"{candidate.name} {candidate.code} {' '.join(candidate.synonyms)}"

        covered = 0
        for token in context.query_tokens:
            if token.lower() in candidate_text.lower():
                covered += 1

        return covered / len(context.query_tokens)


class ExactMatchExtractor(FeatureExtractor):
    """精确匹配特征."""

    def extract(self, candidate: Candidate, context: QueryContext) -> float:
        """检查是否精确匹配."""
        query_lower = context.query.lower()

        # 检查名称、编码、同义词
        if candidate.name.lower() == query_lower:
            return 1.0
        if candidate.code.lower() == query_lower:
            return 1.0
        if any(s.lower() == query_lower for s in candidate.synonyms):
            return 1.0

        return 0.0


class PrefixMatchExtractor(FeatureExtractor):
    """前缀匹配特征."""

    def extract(self, candidate: Candidate, context: QueryContext) -> float:
        """检查是否前缀匹配."""
        query_lower = context.query.lower()

        if candidate.name.lower().startswith(query_lower):
            return 1.0
        if candidate.code.lower().startswith(query_lower):
            return 1.0

        return 0.0


# ==================== 业务域特征 ====================


class DomainMatchExtractor(FeatureExtractor):
    """业务域匹配特征."""

    def extract(self, candidate: Candidate, context: QueryContext) -> float:
        """检查业务域是否匹配."""
        if not context.query_domain:
            return 0.5  # 未知业务域时返回中性值

        return 1.0 if candidate.domain == context.query_domain else 0.0


# ==================== 召回来源特征 ====================


class RecallSourceExtractor(FeatureExtractor):
    """召回来源特征."""

    def extract(self, candidate: Candidate, context: QueryContext) -> float:
        """召回来源编码."""
        source_map = {
            "vector": 0.0,
            "graph": 0.5,
            "both": 1.0,
        }
        return source_map.get(candidate.source, 0.0)


# ==================== 组合特征 ====================


class CombinedScoreExtractor(FeatureExtractor):
    """组合分数特征."""

    def extract(self, candidate: Candidate, context: QueryContext) -> float:
        """计算组合分数（向量 + 图谱）."""
        # 向量 0.7 + 图谱 0.3 + 重要性 0.1
        return candidate.vector_score * 0.7 + candidate.graph_score * 0.3 + candidate.importance * 0.1


class TextRelevanceExtractor(FeatureExtractor):
    """文本相关性特征."""

    def extract(self, candidate: Candidate, context: QueryContext) -> float:
        """计算文本相关性."""
        query_lower = context.query.lower()

        # 名称匹配（权重最高）
        if query_lower in candidate.name.lower():
            name_score = 1.0
        else:
            name_score = 0.0

        # 编码匹配
        if query_lower in candidate.code.lower():
            code_score = 1.0
        else:
            code_score = 0.0

        # 同义词匹配
        synonym_score = sum(
            1.0 for s in candidate.synonyms if query_lower in s.lower()
        ) / max(len(candidate.synonyms), 1)

        # 描述匹配
        if query_lower in candidate.description.lower():
            desc_score = 0.5
        else:
            desc_score = 0.0

        # 加权组合
        return name_score * 0.5 + code_score * 0.3 + synonym_score * 0.15 + desc_score * 0.05


class FeatureExtractorFactory:
    """特征提取器工厂."""

    # 标准特征集（11个特征）
    STANDARD_FEATURES = [
        VectorSimilarityExtractor(),
        GraphScoreExtractor(),
        ImportanceExtractor(),
        QueryCoverageExtractor(),
        ExactMatchExtractor(),
        PrefixMatchExtractor(),
        DomainMatchExtractor(),
        RecallSourceExtractor(),
        CombinedScoreExtractor(),
        TextRelevanceExtractor(),
    ]

    @classmethod
    def create_standard_extractors(cls) -> list[FeatureExtractor]:
        """创建标准特征提取器列表.

        Returns:
            特征提取器列表
        """
        return cls.STANDARD_FEATURES.copy()

    @classmethod
    def extract_all_features(
        cls,
        candidate: Candidate,
        context: QueryContext,
        extractors: list[FeatureExtractor] | None = None,
    ) -> FeatureVector:
        """提取所有特征.

        Args:
            candidate: 候选指标
            context: 查询上下文
            extractors: 特征提取器列表（默认使用标准特征集）

        Returns:
            特征向量
        """
        if extractors is None:
            extractors = cls.STANDARD_FEATURES

        features = {}
        for extractor in extractors:
            try:
                value = extractor.extract(candidate, context)
                features[extractor.name] = value
            except Exception as e:
                print(f"特征提取失败 {extractor.name}: {e}")
                features[extractor.name] = 0.0

        return FeatureVector(features=features)
