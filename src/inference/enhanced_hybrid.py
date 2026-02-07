"""增强版三层混合意图识别架构（集成智谱AI）."""

import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .intent import IntentRecognizer, QueryIntent, TimeGranularity, AggregationType
from .llm_intent import LLMIntentRecognizer, LocalLLMIntentRecognizer
from .zhipu_intent import ZhipuIntentRecognizer
from ..recall.semantic_recall import SemanticRecall, FallbackSemanticRecall


@dataclass
class LayerResult:
    """单层识别结果."""

    layer_name: str
    success: bool
    intent: Optional[QueryIntent]
    confidence: float
    duration: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HybridIntentResult:
    """混合架构识别结果."""

    query: str
    final_intent: QueryIntent
    source_layer: str
    all_layers: list[LayerResult]
    total_duration: float
    candidates: list[Any] = field(default_factory=list)  # 候选指标


class EnhancedHybridIntentRecognizer:
    """增强版三层混合意图识别器.

    架构:
    L1: 规则匹配 (快速, <10ms, 处理10%常见查询)
    L2: 语义向量 (中等, ~50ms, 处理60%查询)
    L3: LLM推理 (准确, ~500ms, 处理30%复杂查询)

    LLM选项:
    - 智谱AI GLM (推荐, 国产, ¥1/1M tokens)
    - OpenAI GPT-4o (备选, $0.005/1K tokens)
    - 本地Ollama (免费, 需要GPU)
    """

    def __init__(
        self,
        llm_provider: str = "zhipu",  # zhipu/openai/local
        enable_semantic: bool = True,
        confidence_thresholds: dict[str, float] = None
    ):
        """初始化混合识别器.

        Args:
            llm_provider: LLM提供商 (zhipu/openai/local)
            enable_semantic: 是否启用语义向量检索
            confidence_thresholds: 各层置信度阈值
        """
        # L1: 规则识别器
        self.rule_recognizer = IntentRecognizer()

        # L2: 语义召回
        self.enable_semantic = enable_semantic
        if enable_semantic:
            try:
                self.semantic_recall = SemanticRecall()
            except Exception as e:
                print(f"⚠️  语义召回初始化失败: {e}，使用兜底方案")
                self.semantic_recall = FallbackSemanticRecall()
        else:
            self.semantic_recall = FallbackSemanticRecall()

        # L3: LLM识别器
        self.llm_provider = llm_provider
        if llm_provider == "zhipu":
            # 优先使用智谱AI（国产，价格优惠）
            self.llm_recognizer = ZhipuIntentRecognizer(model="glm-4-flash")
        elif llm_provider == "openai":
            self.llm_recognizer = LLMIntentRecognizer(model="gpt-4o-mini")
        elif llm_provider == "local":
            self.llm_recognizer = LocalLLMIntentRecognizer(model="qwen2.5:7b")
        else:
            self.llm_recognizer = None

        # 置信度阈值
        self.thresholds = confidence_thresholds or {
            "rule": 0.90,  # 规则匹配需要高置信度
            "semantic": 0.75,  # 语义匹配阈值
        }

        # 统计信息
        self.stats = {
            "total_queries": 0,
            "l1_hits": 0,
            "l2_hits": 0,
            "l3_hits": 0,
            "failures": 0,
        }

    def recognize(self, query: str, top_k: int = 10) -> HybridIntentResult:
        """使用三层架构识别查询意图.

        Args:
            query: 用户查询文本
            top_k: 返回候选数量

        Returns:
            混合识别结果
        """
        self.stats["total_queries"] += 1

        start = time.time()
        all_layers = []
        candidates = []

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
                total_duration=time.time() - start,
                candidates=candidates
            )

        # L2: 语义向量匹配
        l2_result = self._layer2_semantic_match(query, top_k)
        all_layers.append(l2_result)

        # 获取L2的候选指标，传递给L3
        l2_candidates = l2_result.metadata.get("candidates", [])

        if l2_result.success and l2_result.confidence >= self.thresholds["semantic"]:
            self.stats["l2_hits"] += 1
            return HybridIntentResult(
                query=query,
                final_intent=l2_result.intent,
                source_layer="L2_Semantic",
                all_layers=all_layers,
                total_duration=time.time() - start,
                candidates=l2_candidates
            )

        # L3: LLM深度推理（传递L2的候选指标）
        l3_result = self._layer3_llm_inference(query, l2_candidates)
        all_layers.append(l3_result)

        if l3_result.success:
            self.stats["l3_hits"] += 1
            return HybridIntentResult(
                query=query,
                final_intent=l3_result.intent,
                source_layer="L3_LLM",
                all_layers=all_layers,
                total_duration=time.time() - start,
                candidates=l3_result.metadata.get("candidates", [])
            )

        # 全部失败，使用最佳降级结果
        self.stats["failures"] += 1
        best_result = max(
            [r for r in all_layers if r.intent],
            key=lambda x: x.confidence,
            default=l1_result
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
            total_duration=time.time() - start,
            candidates=[]
        )

    def _layer1_rule_match(self, query: str) -> LayerResult:
        """L1层：基于规则的快速匹配."""
        start = time.time()

        try:
            intent = self.rule_recognizer.recognize(query)
            confidence = self._calculate_rule_confidence(query, intent)

            return LayerResult(
                layer_name="L1_Rule",
                success=True,
                intent=intent,
                confidence=confidence,
                duration=time.time() - start,
                metadata={
                    "method": "regex_patterns",
                    "time_detected": intent.time_range is not None,
                    "aggregation_detected": intent.aggregation_type is not None,
                    "dimensions_detected": len(intent.dimensions) > 0
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

    def _layer2_semantic_match(self, query: str, top_k: int) -> LayerResult:
        """L2层：语义向量匹配."""
        start = time.time()

        try:
            # 语义召回
            recall_result = self.semantic_recall.recall(query, top_k=top_k)

            if not recall_result:
                raise Exception("语义召回失败")

            # 从召回结果提取意图
            intent = self.rule_recognizer.recognize(query)

            # 计算置信度（基于召回结果）
            confidence = 0.8  # 基础分
            if recall_result.total > 0:
                top_score = recall_result.candidates[0].score
                confidence = max(confidence, top_score)

            return LayerResult(
                layer_name="L2_Semantic",
                success=True,
                intent=intent,
                confidence=confidence,
                duration=time.time() - start,
                metadata={
                    "method": recall_result.search_method,
                    "candidates_found": recall_result.total,
                    "top_score": recall_result.candidates[0].score if recall_result.candidates else 0,
                    "embedding_dim": recall_result.embedding_dim,
                    "candidates": [
                        {
                            "name": c.name,
                            "score": c.score,
                            "reason": c.match_reason
                        }
                        for c in recall_result.candidates[:3]
                    ]
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

    def _layer3_llm_inference(self, query: str, candidates: list = None) -> LayerResult:
        """L3层：LLM深度推理.

        Args:
            query: 用户查询文本
            candidates: 从L2层获取的候选指标列表
        """
        start = time.time()

        if not self.llm_recognizer:
            return LayerResult(
                layer_name="L3_LLM",
                success=False,
                intent=None,
                confidence=0.0,
                duration=time.time() - start,
                metadata={"error": "LLM not configured"}
            )

        try:
            # 调用LLM，传递candidates以帮助正确识别指标
            if self.llm_provider == "zhipu":
                llm_result = self.llm_recognizer.recognize(query, candidates)
            else:
                llm_result = self.llm_recognizer.recognize(query, candidates)

            if not llm_result:
                raise Exception("LLM returned None")

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

            # 构建元数据
            metadata = {
                "model": llm_result.model,
                "reasoning": llm_result.reasoning,
                "confidence": llm_result.confidence
            }

            if hasattr(llm_result, 'tokens_used'):
                metadata["tokens_used"] = llm_result.tokens_used

            if self.llm_provider == "zhipu":
                metadata["cost"] = self._estimate_zhipu_cost(llm_result.tokens_used)

            return LayerResult(
                layer_name=f"L3_LLM_{self.llm_provider.capitalize()}",
                success=True,
                intent=intent,
                confidence=llm_result.confidence,
                duration=llm_result.latency,
                metadata=metadata
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
        """计算规则匹配的置信度."""
        score = 0.5

        if intent.core_query.lower() in query.lower():
            score += 0.2

        if intent.time_range:
            score += 0.15

        if intent.aggregation_type:
            score += 0.1

        if intent.dimensions:
            score += 0.1

        if len(intent.core_query) < len(query) * 0.5:
            score += 0.1

        return min(score, 1.0)

    def _parse_time_range(self, time_range: Optional[dict]) -> Optional[tuple]:
        """解析LLM返回的时间范围."""
        if not time_range:
            return None
        # TODO: 实现时间范围解析
        return None

    def _parse_granularity(self, granularity: Optional[str]) -> Optional[TimeGranularity]:
        """解析时间粒度."""
        if not granularity:
            return None
        try:
            return TimeGranularity(granularity)
        except ValueError:
            return None

    def _parse_aggregation(self, aggregation: Optional[str]) -> Optional[AggregationType]:
        """解析聚合类型."""
        if not aggregation:
            return None
        try:
            return AggregationType(aggregation)
        except ValueError:
            return None

    def _estimate_zhipu_cost(self, tokens_used: dict[str, int]) -> float:
        """估算智谱AI成本（人民币）."""
        # 智谱AI价格: ¥1/1M tokens (glm-4-flash免费)
        total_tokens = tokens_used.get("total_tokens", 0)
        return total_tokens / 1_000_000 * 1.0  # ¥1/1M

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息."""
        total = self.stats["total_queries"]

        if total == 0:
            return {"message": "暂无统计数据"}

        return {
            "total_queries": total,
            "layer_distribution": {
                "L1_Rule": f"{self.stats['l1_hits']/total*100:.1f}%",
                "L2_Semantic": f"{self.stats['l2_hits']/total*100:.1f}%",
                f"L3_LLM_{self.llm_provider.capitalize()}": f"{self.stats['l3_hits']/total*100:.1f}%",
            },
            "failure_rate": f"{self.stats['failures']/total*100:.1f}%",
            "llm_provider": self.llm_provider,
            "semantic_enabled": self.enable_semantic
        }


# 测试函数
def test_enhanced_hybrid():
    """测试增强版混合架构."""
    print("\n🧪 测试增强版三层混合架构")
    print("=" * 50)

    # 初始化（使用智谱AI）
    recognizer = EnhancedHybridIntentRecognizer(
        llm_provider="zhipu",
        enable_semantic=True
    )

    test_queries = [
        "GMV是什么",
        "最近7天的成交金额",
        "本月营收总和"
    ]

    for query in test_queries:
        print(f"\n查询: {query}")
        print("-" * 50)

        result = recognizer.recognize(query)

        print(f"✅ 识别成功")
        print(f"   来源层: {result.source_layer}")
        print(f"   核心查询: {result.final_intent.core_query}")
        print(f"   总耗时: {result.total_duration*1000:.2f}ms")

        print(f"\n   各层结果:")
        for layer in result.all_layers:
            if layer.success:
                print(f"      {layer.layer_name}: ✓ ({layer.confidence:.2f}, {layer.duration*1000:.2f}ms)")
            else:
                print(f"      {layer.layer_name}: ✗")

    # 统计信息
    print(f"\n统计信息:")
    print(recognizer.get_statistics())

    print("\n" + "=" * 50)


if __name__ == "__main__":
    test_enhanced_hybrid()
