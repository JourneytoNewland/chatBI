"""增强版三层混合意图识别架构（集成智谱AI）."""

import asyncio
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .intent import IntentRecognizer, QueryIntent, TimeGranularity, AggregationType
from .llm_intent import LLMIntentRecognizer, LocalLLMIntentRecognizer
from .zhipu_intent import ZhipuIntentRecognizer
from ..recall.semantic_recall import SemanticRecall, FallbackSemanticRecall
from ..recall.dual_recall import DualRecall
from ..recall.vector.qdrant_store import QdrantVectorStore
from ..recall.vector.vectorizer import MetricVectorizer
from ..recall.graph.neo4j_client import Neo4jClient
from ..rerank.ranker import RuleBasedRanker
from ..rerank.models import Candidate, QueryContext


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
        enable_dual_recall: bool = True,  # 新增：是否启用双路召回
        enable_rerank: bool = True,  # 新增：是否启用精排
        confidence_thresholds: dict[str, float] = None
    ):
        """初始化混合识别器.

        Args:
            llm_provider: LLM提供商 (zhipu/openai/local)
            enable_semantic: 是否启用语义向量检索
            enable_dual_recall: 是否启用双路召回（向量+图谱）
            enable_rerank: 是否启用11维特征精排
            confidence_thresholds: 各层置信度阈值
        """
        # L1: 规则识别器
        self.rule_recognizer = IntentRecognizer()

        # L2: 语义召回（保留向后兼容）
        self.enable_semantic = enable_semantic
        if enable_semantic:
            try:
                self.semantic_recall = SemanticRecall()
            except Exception as e:
                print(f"⚠️  语义召回初始化失败: {e}，使用兜底方案")
                self.semantic_recall = FallbackSemanticRecall()
        else:
            self.semantic_recall = FallbackSemanticRecall()

        # L2增强: 双路召回融合
        self.enable_dual_recall = enable_dual_recall
        self.dual_recall = None
        if enable_dual_recall:
            try:
                # 使用与系统相同的向量模型
                import os
                model_name = os.getenv('VECTORIZER_MODEL_NAME', 'sentence-transformers/all-MiniLM-L6-v2')
                vectorizer = MetricVectorizer(model_name=model_name)
                vector_store = QdrantVectorStore()
                neo4j_client = Neo4jClient()
                self.dual_recall = DualRecall(vectorizer, vector_store, neo4j_client)
                print("✅ 双路召回初始化成功")
            except Exception as e:
                print(f"⚠️  双路召回初始化失败: {e}，使用单一语义召回")
                self.dual_recall = None

        # L2增强: 融合精排
        self.enable_rerank = enable_rerank
        self.ranker = None
        if enable_rerank:
            try:
                self.ranker = RuleBasedRanker()
                print("✅ 融合精排器初始化成功")
            except Exception as e:
                print(f"⚠️  融合精排器初始化失败: {e}")
                self.ranker = None

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
        """L2层：语义向量匹配（增强版：双路召回 + 融合精排）."""
        start = time.time()

        try:
            # 如果启用了双路召回，使用 DualRecall
            if self.dual_recall is not None:
                return self._dual_recall_with_rerank(query, top_k, start)

            # 否则使用原有的单一语义召回（向后兼容）
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
                    "recall_type": "semantic_only",  # 标识为单一语义召回
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

    def _dual_recall_with_rerank(self, query: str, top_k: int, start_time: float) -> LayerResult:
        """使用双路召回和融合精排的L2层实现.

        Args:
            query: 查询文本
            top_k: 返回数量
            start_time: 开始时间（用于计算耗时）

        Returns:
            LayerResult 包含详细的召回和精排信息
        """
        try:
            # Step 1: 双路召回（使用线程池运行异步代码）
            from concurrent.futures import ThreadPoolExecutor
            import threading

            result_container = []
            exception_container = []

            def run_in_thread():
                """在新线程中运行异步代码"""
                try:
                    # 创建新的事件循环
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)

                    # 运行异步双路召回
                    recall_results = new_loop.run_until_complete(
                        self.dual_recall.dual_recall(
                            query=query,
                            vector_top_k=50,
                            graph_top_k=30,
                            final_top_k=top_k * 2,  # 先召回更多，供精排使用
                            timeout=1.0
                        )
                    )

                    result_container.append(recall_results)
                    new_loop.close()
                except Exception as e:
                    exception_container.append(e)
                finally:
                    # 清理事件循环
                    try:
                        new_loop = asyncio.get_event_loop()
                        if new_loop and not new_loop.is_closed():
                            new_loop.close()
                    except:
                        pass

            # 在线程池中执行
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_in_thread)
                future.result(timeout=5)  # 5秒超时

            # 检查异常
            if exception_container:
                print(f"❌ 双路召回异常: {exception_container[0]}")
                import traceback
                traceback.print_exc()
                raise exception_container[0]

            # 获取结果
            recall_results = result_container[0] if result_container else None

            if not recall_results:
                print(f"⚠️  双路召回返回空结果，result_container={result_container}")
                raise Exception("双路召回未返回结果")

            # Step 2: 转换为 Candidate 对象（用于精排）
            candidates = []
            for result in recall_results:
                candidate = Candidate(
                    metric_id=result.metric_id,
                    name=result.name,
                    code=result.code,
                    description=result.description,
                    domain=result.domain,
                    synonyms=[],  # 可以后续填充
                    importance=0.5,  # 默认重要性
                    formula=None,
                    vector_score=result.vector_score or 0.0,
                    graph_score=result.graph_score or 0.0,
                    source=result.source
                )
                candidates.append(candidate)

            # Step 3: 融合精排
            query_context = QueryContext.from_text(query)
            reranked_results = []

            if self.ranker is not None:
                # 使用精排器
                reranked_results = self.ranker.rerank(candidates, query_context, top_k=top_k)
            else:
                # 降级：按原始分数排序
                reranked_results = [
                    (c, c.vector_score, {})
                    for c in sorted(candidates, key=lambda x: x.vector_score, reverse=True)
                ][:top_k]

            # Step 4: 提取最终意图（使用排名第一的结果）
            top_candidate = reranked_results[0][0] if reranked_results else candidates[0]

            # 使用规则识别器从候选指标中提取完整意图
            intent = self.rule_recognizer.recognize(query)

            # Step 5: 计算置信度（基于精排后的分数）
            top_score = reranked_results[0][1] if reranked_results else 0.0
            confidence = max(0.75, min(0.95, top_score))

            # Step 6: 构建详细的元数据
            metadata = {
                "method": "dual_recall_with_rerank",
                "recall_type": "dual_recall",  # 标识为双路召回
                "vector_top_k": 50,
                "graph_top_k": 30,
                "final_top_k": top_k,
                "candidates_found": len(recall_results),
                "reranked": self.ranker is not None,
                "fusion_stats": self._calculate_fusion_stats(recall_results),
            }

            # 添加召回来源统计
            source_counts = {"vector": 0, "graph": 0, "both": 0}
            for r in recall_results:
                source_counts[r.source] = source_counts.get(r.source, 0) + 1
            metadata["source_distribution"] = source_counts

            # 添加 Top-3 候选的详细信息
            metadata["candidates"] = []
            for i, (candidate, score, details) in enumerate(reranked_results[:3]):
                candidate_info = {
                    "rank": i + 1,
                    "name": candidate.name,
                    "code": candidate.code,
                    "domain": candidate.domain,
                    "final_score": score,
                    "vector_score": candidate.vector_score,
                    "graph_score": candidate.graph_score,
                    "source": candidate.source,
                }

                # 如果有精排详情，添加特征分数
                if details:
                    candidate_info["feature_scores"] = details

                metadata["candidates"].append(candidate_info)

            # 如果启用了精排，添加特征权重信息
            if self.ranker is not None:
                metadata["feature_weights"] = self.ranker.weights

            return LayerResult(
                layer_name="L2_Semantic_Enhanced",
                success=True,
                intent=intent,
                confidence=confidence,
                duration=time.time() - start_time,
                metadata=metadata
            )

        except Exception as e:
            import traceback
            error_details = str(e)
            error_traceback = traceback.format_exc()

            print(f"❌ 双路召回+精排失败: {error_details}")
            print(f"Traceback: {error_traceback}")

            # 降级到单一语义召回
            print("⚠️  降级到单一语义召回")
            return self._layer2_semantic_match_fallback(query, top_k, start_time)

    def _layer2_semantic_match_fallback(self, query: str, top_k: int, start_time: float) -> LayerResult:
        """降级方案：使用单一语义召回."""
        try:
            recall_result = self.semantic_recall.recall(query, top_k=top_k)

            if not recall_result:
                raise Exception("语义召回降级也失败")

            intent = self.rule_recognizer.recognize(query)

            confidence = 0.75  # 降级后置信度降低
            if recall_result.total > 0:
                top_score = recall_result.candidates[0].score
                confidence = max(confidence, top_score * 0.9)

            return LayerResult(
                layer_name="L2_Semantic_Fallback",
                success=True,
                intent=intent,
                confidence=confidence,
                duration=time.time() - start_time,
                metadata={
                    "method": recall_result.search_method,
                    "recall_type": "semantic_fallback",  # 标识为降级方案
                    "fallback_reason": "dual_recall_failed",
                    "candidates_found": recall_result.total,
                    "top_score": recall_result.candidates[0].score if recall_result.candidates else 0,
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
                duration=time.time() - start_time,
                metadata={"error": str(e), "fallback_failed": True}
            )

    def _calculate_fusion_stats(self, recall_results: list) -> dict:
        """计算召回融合的统计信息.

        Args:
            recall_results: 召回结果列表

        Returns:
            统计信息字典
        """
        if not recall_results:
            return {}

        vector_scores = [r.vector_score for r in recall_results if r.vector_score is not None]
        graph_scores = [r.graph_score for r in recall_results if r.graph_score is not None]

        stats = {
            "total_candidates": len(recall_results),
            "vector_avg_score": sum(vector_scores) / len(vector_scores) if vector_scores else 0,
            "graph_avg_score": sum(graph_scores) / len(graph_scores) if graph_scores else 0,
            "vector_max_score": max(vector_scores) if vector_scores else 0,
            "graph_max_score": max(graph_scores) if graph_scores else 0,
        }

        return stats

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
