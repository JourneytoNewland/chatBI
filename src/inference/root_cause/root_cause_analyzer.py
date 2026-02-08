"""根因分析主入口."""

from typing import Any

from src.inference.root_cause.analyzer import (
    AnomalyDetector,
    CausalInferenceEngine,
    DimensionDecomposer,
    RootCauseResult,
    TrendAnalyzer,
)
from src.inference.intent import QueryIntent


class RootCauseAnalyzer:
    """根因分析器.

    L4层核心功能，集成多种分析方法：
    1. 异常检测（统计方法）
    2. 维度分解（贡献度分析）
    3. 趋势分析（时间序列）
    4. 因果推断（业务规则 + LLM）
    5. 报告生成（LLM）
    """

    def __init__(self, llm_client=None):
        """初始化根因分析器.

        Args:
            llm_client: LLM客户端（用于生成报告）
        """
        self.llm_client = llm_client
        self.anomaly_detector = AnomalyDetector()
        self.dimension_decomposer = DimensionDecomposer()
        self.trend_analyzer = TrendAnalyzer()
        self.causal_engine = CausalInferenceEngine()

    def analyze(
        self,
        query: str,
        intent: QueryIntent,
        data: list[dict[str, Any]],
        dimensions_to_analyze: list[str] = None,
    ) -> RootCauseResult:
        """执行根因分析.

        Args:
            query: 用户查询
            intent: 已识别的意图
            data: 查询结果数据
            dimensions_to_analyze: 要分析的维度列表

        Returns:
            根因分析结果
        """
        metric = intent.core_query or "指标"

        # Step 1: 异常检测
        print(f"  [RCA] Step 1: 异常检测...")
        anomalies = self.anomaly_detector.detect_anomalies(data)
        print(f"  [RCA] 检测到 {len(anomalies)} 个异常点")

        # Step 2: 维度分解
        print(f"  [RCA] Step 2: 维度分解...")
        dimensions_to_analyze = dimensions_to_analyze or ["地区", "品类", "渠道"]
        dimensions = []
        for dim in dimensions_to_analyze:
            if dim in data[0] if data else []:
                breakdown = self.dimension_decomposer.decompose(data, dim)
                dimensions.append(breakdown)
                print(f"  [RCA] {dim}维度分解完成: {breakdown.analysis}")

        # Step 3: 趋势分析
        print(f"  [RCA] Step 3: 趋势分析...")
        trends = self.trend_analyzer.analyze(data)
        print(f"  [RCA] 趋势类型: {trends.trend_type}, 强度: {trends.trend_strength:.2f}")

        # Step 4: 因果推断
        print(f"  [RCA] Step 4: 因果推断...")
        causal_factors = self.causal_engine.infer(
            metric=metric,
            trend_type=trends.trend_type,
            anomalies=anomalies,
            dimensions=dimensions,
        )
        print(f"  [RCA] 识别到 {len(causal_factors)} 个潜在原因")

        # Step 5: 生成报告（LLM）
        print(f"  [RCA] Step 5: 生成分析报告...")
        report = self._generate_report(
            query=query,
            metric=metric,
            anomalies=anomalies,
            dimensions=dimensions,
            trends=trends,
            causal_factors=causal_factors,
        )

        # Step 6: 生成行动建议
        recommendations = self._generate_recommendations(
            causal_factors=causal_factors,
            dimensions=dimensions,
        )

        return RootCauseResult(
            query=query,
            metric=metric,
            anomalies=anomalies,
            dimensions=dimensions,
            trends=trends,
            causal_factors=causal_factors,
            report=report,
            recommendations=recommendations,
        )

    def _generate_report(
        self,
        query: str,
        metric: str,
        anomalies: list,
        dimensions: list,
        trends: Any,
        causal_factors: list,
    ) -> str:
        """生成分析报告.

        Args:
            query: 用户查询
            metric: 指标名称
            anomalies: 异常列表
            dimensions: 维度分解结果
            trends: 趋势分析结果
            causal_factors: 因果因素列表

        Returns:
            分析报告文本
        """
        # 如果有LLM，使用LLM生成报告
        if self.llm_client:
            return self._generate_llm_report(
                query=query,
                metric=metric,
                anomalies=anomalies,
                dimensions=dimensions,
                trends=trends,
                causal_factors=causal_factors,
            )

        # 否则使用模板生成报告
        return self._generate_template_report(
            query=query,
            metric=metric,
            anomalies=anomalies,
            dimensions=dimensions,
            trends=trends,
            causal_factors=causal_factors,
        )

    def _generate_llm_report(
        self,
        query: str,
        metric: str,
        anomalies: list,
        dimensions: list,
        trends: Any,
        causal_factors: list,
    ) -> str:
        """使用LLM生成报告.

        Args:
            query: 用户查询
            metric: 指标名称
            anomalies: 异常列表
            dimensions: 维度分解结果
            trends: 趋势分析结果
            causal_factors: 因果因素列表

        Returns:
            LLM生成的报告文本
        """
        # 构建LLM提示
        prompt = f"""你是一位资深的数据分析师。请对以下{metric}指标的分析结果生成一份专业的报告。

用户查询: {query}

分析结果:
1. 异常检测: {len(anomalies)}个异常点
{chr(10).join([f"   - {a.timestamp}: {a.type} (偏离{a.deviation_pct:.1f}%)" for a in anomalies[:3]])}

2. 趋势分析: {trends.trend_type} (强度: {trends.trend_strength:.2f})

3. 维度分解:
{chr(10).join([f"   - {d.dimension_name}: {d.analysis}" for d in dimensions[:2]])}

4. 潜在原因:
{chr(10).join([f"   - {f.name} (置信度: {f.confidence:.0%}): {f.explanation}" for f in causal_factors[:3]])}

请生成一份简洁、专业的分析报告，包括：
1. 核心发现（1-2句话）
2. 主要原因分析（2-3句话）
3. 关键建议（1-2条）

报告风格：专业、简洁、可行动。
"""

        try:
            # 调用LLM生成报告
            response = self.llm_client.generate(
                model="glm-4-flash",
                prompt=prompt,
                max_tokens=500,
            )

            return response.strip() if response else self._generate_template_report(
                query, metric, anomalies, dimensions, trends, causal_factors
            )
        except Exception as e:
            print(f"  [RCA] LLM生成报告失败: {e}")
            return self._generate_template_report(
                query, metric, anomalies, dimensions, trends, causal_factors
            )

    def _generate_template_report(
        self,
        query: str,
        metric: str,
        anomalies: list,
        dimensions: list,
        trends: Any,
        causal_factors: list,
    ) -> str:
        """使用模板生成报告.

        Args:
            query: 用户查询
            metric: 指标名称
            anomalies: 异常列表
            dimensions: 维度分解结果
            trends: 趋势分析结果
            causal_factors: 因果因素列表

        Returns:
            模板生成的报告文本
        """
        report_parts = []

        # 核心发现
        if anomalies:
            top_anomaly = anomalies[0]
            report_parts.append(
                f"在{metric}分析中，检测到{len(anomalies)}个异常点。"
                f"最显著的异常发生在{top_anomaly.timestamp}，"
                f"{top_anomaly.type}了{top_anomaly.deviation_pct:.1f}%。"
            )
        else:
            report_parts.append(
                f"{metric}整体呈现{trends.trend_type}趋势，"
                f"趋势强度为{trends.trend_strength:.2f}。"
            )

        # 主要原因
        if causal_factors:
            top_factors = causal_factors[:2]
            reasons = "、".join([f.name for f in top_factors])
            report_parts.append(f"主要原因是{reasons}。")

            for factor in top_factors:
                report_parts.append(f"- {factor.name}：{factor.explanation}")

        # 关键建议
        if causal_factors:
            actionable_factors = [f for f in causal_factors if f.actionable]
            if actionable_factors:
                report_parts.append(
                    f"建议优先处理{actionable_factors[0].name}问题，"
                    f"这将有助于改善{metric}表现。"
                )

        return "\n".join(report_parts)

    def _generate_recommendations(
        self,
        causal_factors: list,
        dimensions: list,
    ) -> list[str]:
        """生成行动建议.

        Args:
            causal_factors: 因果因素列表
            dimensions: 维度分解结果

        Returns:
            建议列表
        """
        recommendations = []

        # 基于可行动的因果因素生成建议
        for factor in causal_factors:
            if not factor.actionable:
                continue

            if factor.category == "internal":
                if "供应链" in factor.name:
                    recommendations.append("检查库存水平和供应链状态，确保商品供应充足")
                elif "营销" in factor.name:
                    recommendations.append("优化营销策略，提升渠道投放效率")
                elif "产品" in factor.name:
                    recommendations.append("持续产品创新，提升用户体验和粘性")

        # 基于维度分析生成建议
        if dimensions:
            top_dim = dimensions[0]
            if top_dim.top_contributors:
                top_contributor = top_dim.top_contributors[0]
                if top_contributor["contribution_pct"] > 50:
                    recommendations.append(
                        f"优化{top_dim.dimension_name}结构，"
                        f"降低对{top_contributor['name']}的过度依赖"
                    )

        return recommendations[:3]  # 最多返回3条建议
