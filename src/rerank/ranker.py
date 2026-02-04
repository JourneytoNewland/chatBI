"""规则打分器."""

from typing import Any

from src.rerank.features import FeatureExtractorFactory
from src.rerank.models import Candidate, FeatureVector, QueryContext


class RuleBasedRanker:
    """基于规则的精排打分器.

    使用可配置的特征权重计算最终得分。
    """

    # 默认特征权重
    DEFAULT_WEIGHTS = {
        "VectorSimilarityExtractor": 0.30,
        "GraphScoreExtractor": 0.15,
        "ImportanceExtractor": 0.10,
        "QueryCoverageExtractor": 0.08,
        "ExactMatchExtractor": 0.15,
        "PrefixMatchExtractor": 0.05,
        "DomainMatchExtractor": 0.05,
        "RecallSourceExtractor": 0.02,
        "CombinedScoreExtractor": 0.05,
        "TextRelevanceExtractor": 0.05,
    }

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        """初始化打分器.

        Args:
            weights: 特征权重字典（默认使用 DEFAULT_WEIGHTS）
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.extractors = FeatureExtractorFactory.create_standard_extractors()

    def score(
        self,
        candidate: Candidate,
        context: QueryContext,
    ) -> tuple[float, dict[str, float]]:
        """计算候选指标的得分.

        Args:
            candidate: 候选指标
            context: 查询上下文

        Returns:
            (最终得分, 特征明细)
        """
        # 提取所有特征
        feature_vector = FeatureExtractorFactory.extract_all_features(
            candidate,
            context,
            self.extractors,
        )

        # 计算加权得分
        total_score = 0.0
        feature_details = {}

        for extractor in self.extractors:
            feature_name = extractor.name
            feature_value = feature_vector.get(feature_name, 0.0)
            weight = self.weights.get(feature_name, 0.0)

            weighted_score = feature_value * weight
            total_score += weighted_score

            feature_details[feature_name] = {
                "value": feature_value,
                "weight": weight,
                "score": weighted_score,
            }

        # 归一化到 [0, 1]
        total_score = max(0.0, min(1.0, total_score))

        return total_score, feature_details

    def rank(
        self,
        candidates: list[Candidate],
        context: QueryContext,
    ) -> list[tuple[Candidate, float, dict[str, Any]]]:
        """对候选指标列表排序.

        Args:
            candidates: 候选指标列表
            context: 查询上下文

        Returns:
            排序后的列表，每个元素为 (候选, 得分, 特征明细)
        """
        scored_candidates = []

        for candidate in candidates:
            score, details = self.score(candidate, context)
            scored_candidates.append((candidate, score, details))

        # 按得分降序排序
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        return scored_candidates

    def rerank(
        self,
        candidates: list[Candidate],
        context: QueryContext,
        top_k: int = 10,
    ) -> list[tuple[Candidate, float, dict[str, Any]]]:
        """重排序并返回 Top-K.

        Args:
            candidates: 候选指标列表
            context: 查询上下文
            top_k: 返回数量

        Returns:
            Top-K 排序结果
        """
        ranked = self.rank(candidates, context)
        return ranked[:top_k]
