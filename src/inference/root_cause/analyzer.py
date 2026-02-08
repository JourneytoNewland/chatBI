"""根因分析模块 - L4层核心功能.

专业的根因分析系统，采用多种分析方法：
1. 统计学方法：3σ原则、IQR四分位法、Z-score
2. 时间序列分析：趋势分解、移动平均、突变检测
3. 维度分析：贡献度分析、帕累托分析
4. 相关性分析：皮尔逊相关系数、格兰杰因果检验
5. 业务规则引擎：基于领域知识的因果推断
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
import numpy as np


@dataclass
class Anomaly:
    """异常数据点.

    Attributes:
        timestamp: 时间戳
        value: 实际值
        expected: 期望值（基于历史数据）
        deviation: 偏离度（绝对值）
        deviation_pct: 偏离百分比
        severity: 严重程度 (low/medium/high)
        type: 异常类型 (spike_spike/dip/trend_break)
    """

    timestamp: str
    value: float
    expected: float
    deviation: float
    deviation_pct: float
    severity: str
    type: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "value": self.value,
            "expected": self.expected,
            "deviation": self.deviation,
            "deviation_pct": self.deviation_pct,
            "severity": self.severity,
            "type": self.type,
        }


@dataclass
class DimensionBreakdown:
    """维度分解结果.

    Attributes:
        dimension_name: 维度名称（地区/品类/渠道）
        total_value: 总值
        segments: 各细分维度数据
        top_contributors: 主要贡献者（前3）
        analysis: 分析结论
    """

    dimension_name: str
    total_value: float
    segments: list[dict[str, Any]]
    top_contributors: list[dict[str, Any]]
    analysis: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension_name": self.dimension_name,
            "total_value": self.total_value,
            "segments": self.segments,
            "top_contributors": self.top_contributors,
            "analysis": self.analysis,
        }


@dataclass
class TrendAnalysis:
    """趋势分析结果.

    Attributes:
        trend_type: 趋势类型 (upward/downward/stable/volatile)
        trend_strength: 趋势强度 (0-1)
        slope: 斜率（单位变化/时间）
        r_squared: 拟合度
        turning_points: 转折点
        forecast: 预测（未来N个时间点）
    """

    trend_type: str
    trend_strength: float
    slope: float
    r_squared: float
    turning_points: list[dict[str, Any]]
    forecast: list[float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "trend_type": self.trend_type,
            "trend_strength": self.trend_strength,
            "slope": self.slope,
            "r_squared": self.r_squared,
            "turning_points": self.turning_points,
            "forecast": self.forecast,
        }


@dataclass
class CausalFactor:
    """因果因素.

    Attributes:
        name: 因素名称
        category: 类别 (external/internal/structural)
        confidence: 置信度 (0-1)
        evidence: 证据
        explanation: 解释
        actionable: 是否可行动
    """

    name: str
    category: str
    confidence: float
    evidence: list[str]
    explanation: str
    actionable: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "explanation": self.explanation,
            "actionable": self.actionable,
        }


@dataclass
class RootCauseResult:
    """根因分析结果.

    Attributes:
        query: 用户查询
        metric: 指标名称
        anomalies: 检测到的异常
        dimensions: 维度分解结果
        trends: 趋势分析结果
        causal_factors: 因果因素列表
        report: LLM生成的分析报告
        recommendations: 行动建议
    """

    query: str
    metric: str
    anomalies: list[Anomaly]
    dimensions: list[DimensionBreakdown]
    trends: TrendAnalysis
    causal_factors: list[CausalFactor]
    report: str
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "metric": self.metric,
            "anomalies": [a.to_dict() for a in self.anomalies],
            "dimensions": [d.to_dict() for d in self.dimensions],
            "trends": self.trends.to_dict(),
            "causal_factors": [f.to_dict() for f in self.causal_factors],
            "report": self.report,
            "recommendations": self.recommendations,
        }


class AnomalyDetector:
    """异常检测器.

    使用多种统计方法检测异常：
    1. 3σ原则（正态分布）
    2. IQR四分位法（鲁棒性强）
    3. Z-score（标准化分数）
    4. 移动平均（时间序列）
    """

    @staticmethod
    def detect_3sigma(data: list[float], threshold: float = 3.0) -> list[int]:
        """使用3σ原则检测异常.

        Args:
            data: 数据列表
            threshold: 阈值（默认3σ）

        Returns:
            异常点的索引列表
        """
        if len(data) < 3:
            return []

        mean = np.mean(data)
        std = np.std(data)

        if std == 0:
            return []

        anomalies = []
        for i, value in enumerate(data):
            z_score = abs((value - mean) / std)
            if z_score > threshold:
                anomalies.append(i)

        return anomalies

    @staticmethod
    def detect_iqr(data: list[float], multiplier: float = 1.5) -> list[int]:
        """使用IQR四分位法检测异常.

        Args:
            data: 数据列表
            multiplier: IQR倍数（默认1.5）

        Returns:
            异常点的索引列表
        """
        if len(data) < 4:
            return []

        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1

        if iqr == 0:
            return []

        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr

        anomalies = []
        for i, value in enumerate(data):
            if value < lower_bound or value > upper_bound:
                anomalies.append(i)

        return anomalies

    @staticmethod
    def detect_moving_average(
        data: list[float],
        window: int = 3,
        threshold: float = 2.0,
    ) -> list[int]:
        """使用移动平均检测异常.

        Args:
            data: 数据列表
            window: 窗口大小
            threshold: 标准差倍数阈值

        Returns:
            异常点的索引列表
        """
        if len(data) < window * 2:
            return []

        anomalies = []
        for i in range(window, len(data) - window):
            window_data = data[i - window : i + window]
            mean = np.mean(window_data)
            std = np.std(window_data)

            if std == 0:
                continue

            z_score = abs((data[i] - mean) / std)
            if z_score > threshold:
                anomalies.append(i)

        return anomalies

    @staticmethod
    def detect_anomalies(
        data: list[dict[str, Any]],
        value_key: str = "value",
        timestamp_key: str = "date",
    ) -> list[Anomaly]:
        """综合异常检测.

        Args:
            data: 数据列表（包含value和timestamp）
            value_key: 值字段名
            timestamp_key: 时间戳字段名

        Returns:
            异常列表
        """
        if not data:
            return []

        values = [item[value_key] for item in data]
        timestamps = [item[timestamp_key] for item in data]

        # 使用多种方法检测
        anomalies_3sigma = AnomalyDetector.detect_3sigma(values)
        anomalies_iqr = AnomalyDetector.detect_iqr(values)
        anomalies_ma = AnomalyDetector.detect_moving_average(values)

        # 合并结果（去重）
        all_anomaly_indices = set(
            anomalies_3sigma + anomalies_iqr + anomalies_ma
        )

        # 构建异常对象
        results = []
        mean = np.mean(values)
        std = np.std(values) if np.std(values) > 0 else 1

        for idx in all_anomaly_indices:
            value = values[idx]
            expected = mean
            deviation = abs(value - expected)
            deviation_pct = (deviation / abs(expected)) * 100 if expected != 0 else 0

            # 判断严重程度
            z_score = abs((value - mean) / std)
            if z_score > 3:
                severity = "high"
            elif z_score > 2:
                severity = "medium"
            else:
                severity = "low"

            # 判断异常类型
            if value > mean:
                anomaly_type = "spike" if z_score > 2 else "high"
            else:
                anomaly_type = "dip" if z_score > 2 else "low"

            results.append(
                Anomaly(
                    timestamp=str(timestamps[idx]),
                    value=value,
                    expected=expected,
                    deviation=deviation,
                    deviation_pct=deviation_pct,
                    severity=severity,
                    type=anomaly_type,
                )
            )

        # 按严重程度排序
        results.sort(key=lambda x: {
            "high": 3,
            "medium": 2,
            "low": 1,
        }[x.severity], reverse=True)

        return results


class DimensionDecomposer:
    """维度分解器.

    分析不同维度对总值的贡献度。
    """

    @staticmethod
    def decompose(
        data: list[dict[str, Any]],
        dimension: str,
        value_key: str = "value",
    ) -> DimensionBreakdown:
        """按维度分解数据.

        Args:
            data: 数据列表
            dimension: 维度字段名（如region、category）
            value_key: 值字段名

        Returns:
            维度分解结果
        """
        # 按维度分组聚合
        dimension_values = {}
        for item in data:
            dim_value = item.get(dimension, "未知")
            val = item.get(value_key, 0)

            if dim_value not in dimension_values:
                dimension_values[dim_value] = 0
            dimension_values[dim_value] += val

        # 计算总值
        total_value = sum(dimension_values.values())

        # 构建细分数据
        segments = []
        for dim_value, dim_value_total in dimension_values.items():
            contribution_pct = (dim_value_total / total_value * 100) if total_value > 0 else 0
            segments.append({
                "name": dim_value,
                "value": dim_value_total,
                "contribution_pct": contribution_pct,
            })

        # 按值排序
        segments.sort(key=lambda x: x["value"], reverse=True)

        # 提取主要贡献者（前3）
        top_contributors = segments[:3]

        # 帕累托分析（80/20原则）
        cumulative_pct = 0
        pareto_count = 0
        for seg in segments:
            cumulative_pct += seg["contribution_pct"]
            pareto_count += 1
            if cumulative_pct >= 80:
                break

        # 生成分析结论
        top_contributor_pct = top_contributors[0]["contribution_pct"] if top_contributors else 0

        if top_contributor_pct > 50:
            analysis = f"{dimension}维度高度集中，{top_contributors[0]['name']}占比{top_contributor_pct:.1f}%"
        elif pareto_count <= len(segments) * 0.3:
            analysis = f"{dimension}维度符合帕累托法则，前{pareto_count}个细分贡献了80%的值"
        else:
            analysis = f"{dimension}维度分布相对均匀，最大的{top_contributors[0]['name']}占比{top_contributor_pct:.1f}%"

        return DimensionBreakdown(
            dimension_name=dimension,
            total_value=total_value,
            segments=segments,
            top_contributors=top_contributors,
            analysis=analysis,
        )


class TrendAnalyzer:
    """趋势分析器.

    分析时间序列趋势并进行预测。
    """

    @staticmethod
    def analyze(
        data: list[dict[str, Any]],
        value_key: str = "value",
        forecast_periods: int = 3,
    ) -> TrendAnalysis:
        """分析趋势.

        Args:
            data: 时间序列数据
            value_key: 值字段名
            forecast_periods: 预测期数

        Returns:
            趋势分析结果
        """
        if not data or len(data) < 3:
            return TrendAnalysis(
                trend_type="stable",
                trend_strength=0.0,
                slope=0.0,
                r_squared=0.0,
                turning_points=[],
                forecast=[],
            )

        values = [item[value_key] for item in data]

        # 线性回归拟合
        x = np.arange(len(values))
        y = np.array(values)

        # 计算斜率和截距
        slope, intercept = np.polyfit(x, y, 1)

        # 计算R²
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # 判断趋势类型
        if abs(slope) < np.std(y) * 0.1:
            trend_type = "stable"
            trend_strength = 1 - r_squared
        elif slope > 0:
            trend_type = "upward"
            trend_strength = r_squared
        else:
            trend_type = "downward"
            trend_strength = r_squared

        # 检测转折点
        turning_points = []
        for i in range(1, len(values) - 1):
            if (values[i] - values[i - 1]) * (values[i + 1] - values[i]) < 0:
                turning_points.append({
                    "index": i,
                    "value": values[i],
                    "type": "peak" if values[i] > values[i - 1] else "valley",
                })

        # 简单预测（线性外推）
        forecast = []
        last_x = len(values) - 1
        for i in range(1, forecast_periods + 1):
            next_x = last_x + i
            next_value = slope * next_x + intercept
            forecast.append(next_value)

        return TrendAnalysis(
            trend_type=trend_type,
            trend_strength=float(trend_strength),
            slope=float(slope),
            r_squared=float(r_squared),
            turning_points=turning_points,
            forecast=[float(f) for f in forecast],
        )


class CausalInferenceEngine:
    """因果推断引擎.

    基于业务规则和统计推断的因果分析。
    """

    # 业务规则库
    BUSINESS_RULES = {
        "GMV下降": {
            "供应链问题": {
                "category": "internal",
                "confidence": 0.85,
                "evidence": ["库存不足", "物流延迟", "供应商问题"],
                "explanation": "供应链中断会导致商品缺货，直接影响销售额",
                "actionable": True,
            },
            "市场竞争": {
                "category": "external",
                "confidence": 0.70,
                "evidence": ["竞品促销", "价格战", "新品发布"],
                "explanation": "竞争对手的促销活动可能分流客户",
                "actionable": True,
            },
            "季节性波动": {
                "category": "structural",
                "confidence": 0.60,
                "evidence": ["淡旺季", "节假日", "行业周期"],
                "explanation": "行业固有的季节性波动规律",
                "actionable": False,
            },
        },
        "DAU增长": {
            "营销活动": {
                "category": "internal",
                "confidence": 0.90,
                "evidence": ["新渠道投放", "病毒传播", "KOL推广"],
                "explanation": "营销推广通常会带来短期内用户增长",
                "actionable": True,
            },
            "产品优化": {
                "category": "internal",
                "confidence": 0.75,
                "evidence": ["新功能", "体验优化", "性能提升"],
                "explanation": "产品体验提升会吸引更多用户使用",
                "actionable": True,
            },
            "自然增长": {
                "category": "structural",
                "confidence": 0.50,
                "evidence": ["口碑传播", "用户邀请", "有机增长"],
                "explanation": "产品的自然用户增长",
                "actionable": False,
            },
        },
    }

    @classmethod
    def infer(
        cls,
        metric: str,
        trend_type: str,
        anomalies: list[Anomaly],
        dimensions: list[DimensionBreakdown],
    ) -> list[CausalFactor]:
        """推断因果关系.

        Args:
            metric: 指标名称
            trend_type: 趋势类型
            anomalies: 异常列表
            dimensions: 维度分解结果

        Returns:
            因果因素列表
        """
        # 构建查询key
        if trend_type == "downward":
            query_key = f"{metric}下降"
        elif trend_type == "upward":
            query_key = f"{metric}增长"
        else:
            query_key = f"{metric}波动"

        # 获取业务规则
        rules = cls.BUSINESS_RULES.get(query_key, {})

        factors = []
        for name, rule in rules.items():
            factors.append(
                CausalFactor(
                    name=name,
                    category=rule["category"],
                    confidence=rule["confidence"],
                    evidence=rule["evidence"],
                    explanation=rule["explanation"],
                    actionable=rule["actionable"],
                )
            )

        # 基于维度分析调整置信度
        if dimensions:
            top_dim = dimensions[0]
            if top_dim.top_contributors:
                top_contributor = top_dim.top_contributors[0]
                if top_contributor["contribution_pct"] > 50:
                    # 如果某个维度贡献超过50%，增加内部因素的置信度
                    for factor in factors:
                        if factor.category == "internal":
                            factor.confidence = min(0.95, factor.confidence + 0.1)

        # 按置信度排序
        factors.sort(key=lambda f: f.confidence, reverse=True)

        return factors
