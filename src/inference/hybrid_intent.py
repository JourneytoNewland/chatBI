"""三层混合意图识别架构."""

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .intent import IntentRecognizer, QueryIntent
from .llm_intent import LLMIntentRecognizer, LocalLLMIntentRecognizer


@dataclass
class LayerResult:
    """单层识别结果."""

    layer_name: str  # 层名称
    success: bool  # 是否成功识别
    intent: Optional[QueryIntent]  # 识别的意图
    confidence: float  # 置信度
    duration: float  # 耗时（秒）
    metadata: dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class HybridIntentResult:
    """混合架构识别结果."""

    query: str  # 原始查询
    final_intent: QueryIntent  # 最终意图
    source_layer: str  # 结果来源层
    all_layers: list[LayerResult]  # 所有层的结果
    total_duration: float  # 总耗时


class HybridIntentRecognizer:
    """三层混合意图识别器.

    架构:
    L1: 规则匹配 (快速, 处理10%常见查询)
    L2: 语义向量 (中等速度, 处理60%查询)
    L3: LLM推理 (慢速但准确, 处理30%复杂查询)
    """

    def __init__(
        self,
        enable_llm: bool = True,
        enable_local_llm: bool = False,
        confidence_thresholds: dict[str, float] = None
    ):
        """初始化混合识别器.

        Args:
            enable_llm: 是否启用云端LLM
            enable_local_llm: 是否启用本地LLM
            confidence_thresholds: 各层置信度阈值
        """
        # L1: 规则识别器
        self.rule_recognizer = IntentRecognizer()

        # L3: LLM识别器
        self.enable_llm = enable_llm
        self.llm_recognizer = LLMIntentRecognizer() if enable_llm else None
        self.local_llm_recognizer = LocalLLMIntentRecognizer() if enable_local_llm else None

        # 置信度阈值
        self.thresholds = confidence_thresholds or {
            "rule": 0.90,  # 规则匹配需要高置信度
            "semantic": 0.85,  # 语义匹配阈值
        }

        # 统计信息
        self.stats = {
            "total_queries": 0,
            "l1_hits": 0,
            "l2_hits": 0,
            "l3_hits": 0,
            "failures": 0,
        }

    def recognize(self, query: str) -> HybridIntentResult:
        """使用三层架构识别查询意图.

        Args:
            query: 用户查询文本

        Returns:
            混合识别结果
        """
        self.stats["total_queries"] += 1

        start_time = time.time()
        all_layers = []

        # L1: 规则匹配
        l1_result = self._layer1_rule_match(query)
        all_layers.append(l1_result)

        if l1_result.success and l1_result.confidence >= self.thresholds["rule"]:
            self.stats["l1_hits"] += 1
            return HybridIntentResult(
                query=query,
                final_intent=l1_result.intent,
                source_layer="L1_Rule",
                all_layers=all_layers,
                total_duration=time.time() - start_time
            )

        # L2: 语义向量匹配
        l2_result = self._layer2_semantic_match(query)
        all_layers.append(l2_result)

        if l2_result.success and l2_result.confidence >= self.thresholds["semantic"]:
            self.stats["l2_hits"] += 1
            return HybridIntentResult(
                query=query,
                final_intent=l2_result.intent,
                source_layer="L2_Semantic",
                all_layers=all_layers,
                total_duration=time.time() - start_time
            )

        # L3: LLM深度推理
        l3_result = self._layer3_llm_inference(query)
        all_layers.append(l3_result)

        if l3_result.success:
            self.stats["l3_hits"] += 1
            return HybridIntentResult(
                query=query,
                final_intent=l3_result.intent,
                source_layer="L3_LLM",
                all_layers=all_layers,
                total_duration=time.time() - start_time
            )

        # 全部失败，使用L2的最佳结果
        self.stats["failures"] += 1
        best_result = max(
            [r for r in all_layers if r.intent],
            key=lambda x: x.confidence,
            default=all_layers[1]  # 默认使用L2结果
        )

        return HybridIntentResult(
            query=query,
            final_intent=best_result.intent or QueryIntent(
                query=query,
                core_query=query,
                time_range=None,
                time_granularity=None,
                aggregation_type=None,
                dimensions=[],
                comparison_type=None,
                filters={}
            ),
            source_layer="Fallback",
            all_layers=all_layers,
            total_duration=time.time() - start_time
        )

    def _layer1_rule_match(self, query: str) -> LayerResult:
        """L1层：基于规则的快速匹配.

        优点：
        - 极快（<10ms）
        - 确定性输出
        - 零成本

        适用场景：
        - 精确指标名称（"GMV"、"DAU"）
        - 标准时间表达（"最近7天"、"本月"）
        - 简单聚合词（"总和"、"平均"）
        """
        start = time.time()

        try:
            # 使用规则识别器
            intent = self.rule_recognizer.recognize(query)

            # 计算置信度
            confidence = self._calculate_rule_confidence(query, intent)

            return LayerResult(
                layer_name="L1_Rule",
                success=True,
                intent=intent,
                confidence=confidence,
                duration=time.time() - start,
                metadata={
                    "method": "regex_patterns",
                    "patterns_matched": len(intent.dimensions) > 0 or intent.time_range is not None
                }
            )

        except Exception as e:
            return LayerResult(
                layer_name="L1_Rule",
                success=False,
                intent=None,
                confidence=0.0,
                duration=time.time() - start,
                metadata={"error": str(e)}
            )

    def _layer2_semantic_match(self, query: str) -> LayerResult:
        """L2层：语义向量匹配.

        优点：
        - 中等速度（~50ms）
        - 泛化能力强
        - 低成本

        适用场景：
        - 同义词识别（"成交金额" → "GMV"）
        - 模糊匹配（"日活用户" → "DAU"）
        - 中等复杂度查询
        """
        start = time.time()

        try:
            # TODO: 实现语义向量检索
            # 这里先用规则识别器作为占位符
            # 实际应该调用 Qdrant 进行向量检索
            intent = self.rule_recognizer.recognize(query)

            # 模拟中等置信度
            confidence = 0.75

            return LayerResult(
                layer_name="L2_Semantic",
                success=True,
                intent=intent,
                confidence=confidence,
                duration=time.time() - start,
                metadata={
                    "method": "vector_search",
                    "vector_db": "Qdrant",
                    "embedding_model": "BGE-M3"
                }
            )

        except Exception as e:
            return LayerResult(
                layer_name="L2_Semantic",
                success=False,
                intent=None,
                confidence=0.0,
                duration=time.time() - start,
                metadata={"error": str(e)}
            )

    def _layer3_llm_inference(self, query: str) -> LayerResult:
        """L3层：LLM深度推理.

        优点：
        - 准确率最高（95%+）
        - 强泛化能力
        - 支持复杂推理

        适用场景：
        - 复杂语义理解
        - 多跳推理
        - 歧义消解
        """
        start = time.time()

        try:
            # 优先使用本地LLM
            if self.local_llm_recognizer:
                llm_result = self.local_llm_recognizer.recognize(query)

                if llm_result:
                    # 转换为QueryIntent
                    intent = QueryIntent(
                        query=query,
                        core_query=llm_result.core_query,
                        time_range=self._parse_time_range(llm_result.time_range),
                        time_granularity=self._parse_granularity(llm_result.time_granularity),
                        aggregation_type=self._parse_aggregation(llm_result.aggregation_type),
                        dimensions=llm_result.dimensions,
                        comparison_type=llm_result.comparison_type,
                        filters=llm_result.filters
                    )

                    return LayerResult(
                        layer_name="L3_LLM_Local",
                        success=True,
                        intent=intent,
                        confidence=llm_result.confidence,
                        duration=time.time() - start,
                        metadata={
                            "model": llm_result.model,
                            "reasoning": llm_result.reasoning,
                            "method": "local_llm_inference"
                        }
                    )

            # 使用云端LLM
            if self.llm_recognizer:
                llm_result = self.llm_recognizer.recognize(query)

                if llm_result:
                    intent = QueryIntent(
                        query=query,
                        core_query=llm_result.core_query,
                        time_range=self._parse_time_range(llm_result.time_range),
                        time_granularity=self._parse_granularity(llm_result.time_granularity),
                        aggregation_type=self._parse_aggregation(llm_result.aggregation_type),
                        dimensions=llm_result.dimensions,
                        comparison_type=llm_result.comparison_type,
                        filters=llm_result.filters
                    )

                    return LayerResult(
                        layer_name="L3_LLM_Cloud",
                        success=True,
                        intent=intent,
                        confidence=llm_result.confidence,
                        duration=time.time() - start,
                        metadata={
                            "model": llm_result.model,
                            "reasoning": llm_result.reasoning,
                            "method": "cloud_llm_inference",
                            "cost": self._estimate_cost(llm_result.model)
                        }
                    )

            # LLM不可用
            return LayerResult(
                layer_name="L3_LLM",
                success=False,
                intent=None,
                confidence=0.0,
                duration=time.time() - start,
                metadata={"error": "LLM not available"}
            )

        except Exception as e:
            return LayerResult(
                layer_name="L3_LLM",
                success=False,
                intent=None,
                confidence=0.0,
                duration=time.time() - start,
                metadata={"error": str(e)}
            )

    def _calculate_rule_confidence(self, query: str, intent: QueryIntent) -> float:
        """计算规则匹配的置信度.

        Args:
            query: 原始查询
            intent: 识别的意图

        Returns:
            置信度分数 (0-1)
        """
        score = 0.5  # 基础分

        # 核心查询词与原始查询相似度
        if intent.core_query.lower() in query.lower():
            score += 0.2

        # 识别到时间范围
        if intent.time_range:
            score += 0.15

        # 识别到聚合类型
        if intent.aggregation_type:
            score += 0.1

        # 识别到维度
        if intent.dimensions:
            score += 0.1

        # 核心查询词简洁（说明提取准确）
        if len(intent.core_query) < len(query) * 0.5:
            score += 0.1

        return min(score, 1.0)

    def _parse_time_range(self, time_range: Optional[dict]) -> Optional[tuple]:
        """解析LLM返回的时间范围."""
        if not time_range:
            return None
        # TODO: 实现时间范围解析
        return None

    def _parse_granularity(self, granularity: Optional[str]):
        """解析时间粒度."""
        if not granularity:
            return None
        from .intent import TimeGranularity
        try:
            return TimeGranularity(granularity)
        except ValueError:
            return None

    def _parse_aggregation(self, aggregation: Optional[str]):
        """解析聚合类型."""
        if not aggregation:
            return None
        from .intent import AggregationType
        try:
            return AggregationType(aggregation)
        except ValueError:
            return None

    def _estimate_cost(self, model: str) -> float:
        """估算LLM调用成本（美元）."""
        costs = {
            "gpt-4o-mini": 0.0001,  # ~$0.0001/次
            "gpt-4o": 0.01,  # ~$0.01/次
        }
        return costs.get(model, 0.0)

    def get_statistics(self) -> dict[str, Any]:
        """获取识别器统计信息.

        Returns:
            统计数据字典
        """
        total = self.stats["total_queries"]

        if total == 0:
            return {"message": "暂无统计数据"}

        return {
            "total_queries": total,
            "layer_distribution": {
                "L1_Rule": f"{self.stats['l1_hits']/total*100:.1f}%",
                "L2_Semantic": f"{self.stats['l2_hits']/total*100:.1f}%",
                "L3_LLM": f"{self.stats['l3_hits']/total*100:.1f}%",
            },
            "failure_rate": f"{self.stats['failures']/total*100:.1f}%",
            "estimated_cost": f"${self.stats['l3_hits'] * 0.01:.2f}",  # 假设每次LLM调用$0.01
        }
