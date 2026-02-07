"""根因分析模块."""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .metrics import registry
from .mql import MQLQuery, TimeRange
from .engine import MQLExecutionEngine


@dataclass
class RootCause:
    """根因."""
    cause_type: str  # 维度异常、趋势变化、外部因素
    description: str
    severity: str  # high, medium, low
    confidence: float  # 0-1
    evidence: Dict[str, Any]
    suggestions: List[str]


class RootCauseAnalyzer:
    """根因分析器.

    功能:
    1. 检测指标异常
    2. 分析维度下钻
    3. 识别关键影响因素
    4. 提供改进建议
    """

    def __init__(self):
        """初始化根因分析器."""
        self.engine = MQLExecutionEngine()

    def analyze(
        self,
        metric: str,
        time_range: TimeRange,
        threshold: Optional[float] = None,
        dimensions: Optional[List[str]] = None
    ) -> List[RootCause]:
        """执行根因分析.

        Args:
            metric: 指标名称
            time_range: 时间范围
            threshold: 异常阈值
            dimensions: 分析维度

        Returns:
            根因列表
        """
        root_causes = []

        # 1. 获取指标定义
        metric_def = registry.get_metric(metric)
        if not metric_def:
            return [RootCause(
                cause_type="指标不存在",
                description=f"指标 '{metric}' 未在系统中注册",
                severity="high",
                confidence=1.0,
                evidence={},
                suggestions=["检查指标名称是否正确", "查看可用指标列表"]
            )]

        # 2. 检测数据异常
        data_anomaly = self._detect_data_anomaly(metric, time_range, metric_def)
        if data_anomaly:
            root_causes.append(data_anomaly)

        # 3. 维度下钻分析
        dimension_causes = self._analyze_dimensions(metric, time_range, dimensions or metric_def.get("dimensions", []))
        root_causes.extend(dimension_causes)

        # 4. 趋势分析
        trend_cause = self._analyze_trend(metric, time_range, metric_def)
        if trend_cause:
            root_causes.append(trend_cause)

        # 5. 相关指标分析
        related_cause = self._analyze_related_metrics(metric, time_range, metric_def)
        if related_cause:
            root_causes.append(related_cause)

        # 按严重程度和置信度排序
        root_causes.sort(
            key=lambda x: (
                {"high": 3, "medium": 2, "low": 1}.get(x.severity, 0),
                x.confidence
            ),
            reverse=True
        )

        return root_causes[:10]  # 返回Top10

    def _detect_data_anomaly(
        self,
        metric: str,
        time_range: TimeRange,
        metric_def: Dict[str, Any]
    ) -> Optional[RootCause]:
        """检测数据异常."""
        # 执行查询获取数据
        mql_query = MQLQuery(
            metric=metric,
            time_range=time_range
        )

        result = self.engine.execute(mql_query)
        data = result.get("result", [])

        if not data:
            return None

        # 计算统计信息
        values = [row["value"] for row in data]
        avg = sum(values) / len(values)
        min_val = min(values)
        max_val = max(values)

        # 检测异常点（超过平均值2倍标准差）
        import statistics
        if len(values) > 2:
            std = statistics.stdev(values)
            anomalies = [
                v for v in values
                if abs(v - avg) > 2 * std
            ]

            if anomalies:
                return RootCause(
                    cause_type="数据异常",
                    description=f"发现{len(anomalies)}个异常数据点（正常范围: {avg-2*std:.2f} ~ {avg+2*std:.2f}）",
                    severity="high",
                    confidence=0.85,
                    evidence={
                        "anomaly_count": len(anomalies),
                        "anomaly_values": anomalies[:5],
                        "mean": avg,
                        "std": std
                    },
                    suggestions=[
                        "检查数据采集是否正常",
                        "确认是否存在业务活动异常",
                        "分析异常发生的时间点"
                    ]
                )

        return None

    def _analyze_dimensions(
        self,
        metric: str,
        time_range: TimeRange,
        dimensions: List[str]
    ) -> List[RootCause]:
        """分析维度下钻."""
        causes = []

        for dimension in dimensions[:3]:  # 最多分析3个维度
            # 创建分组查询
            mql_query = MQLQuery(
                metric=metric,
                time_range=time_range
            )

            result = self.engine.execute(mql_query)
            data = result.get("result", [])

            if not data:
                continue

            # 模拟按维度分组的数据
            dimension_values = {}
            for row in data:
                dim_value = row.get(dimension, "未知")
                if dim_value not in dimension_values:
                    dimension_values[dim_value] = []
                dimension_values[dim_value].append(row["value"])

            # 找出表现最差的维度值
            dim_stats = []
            for dim_value, values in dimension_values.items():
                avg = sum(values) / len(values)
                dim_stats.append({
                    "dimension": dimension,
                    "value": dim_value,
                    "average": avg,
                    "count": len(values)
                })

            dim_stats.sort(key=lambda x: x["average"])

            if dim_stats and dim_stats[0]["average"] < dim_stats[-1]["average"] * 0.7:
                worst = dim_stats[0]
                best = dim_stats[-1]

                causes.append(RootCause(
                    cause_type="维度异常",
                    description=f"'{dimension}'维度中，'{worst['value']}'表现最差（平均{worst['average']:.2f}），比最佳值'{best['value']}'（{best['average']:.2f}）低{(1-worst['average']/best['average'])*100:.1f}%",
                    severity="medium",
                    confidence=0.75,
                    evidence={
                        "dimension": dimension,
                        "worst_value": worst,
                        "best_value": best
                    },
                    suggestions=[
                        f"重点优化'{worst['value']}'地区/渠道的运营策略",
                        f"学习'{best['value']}'的成功经验并推广",
                        f"分析'{worst['value']}'的具体问题（获客、转化、服务等）"
                    ]
                ))

        return causes

    def _analyze_trend(
        self,
        metric: str,
        time_range: TimeRange,
        metric_def: Dict[str, Any]
    ) -> Optional[RootCause]:
        """分析趋势."""
        # 获取数据
        mql_query = MQLQuery(
            metric=metric,
            time_range=time_range
        )

        result = self.engine.execute(mql_query)
        data = result.get("result", [])

        if len(data) < 3:
            return None

        # 计算趋势
        values = [row["value"] for row in data]
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        if avg_second < avg_first * 0.9:  # 下降超过10%
            return RootCause(
                cause_type="趋势下降",
                description=f"指标呈下降趋势，前半段平均{avg_first:.2f}，后半段平均{avg_second:.2f}，下降{(1-avg_second/avg_first)*100:.1f}%",
                severity="high",
                confidence=0.8,
                evidence={
                    "first_half_avg": avg_first,
                    "second_half_avg": avg_second,
                    "decline_rate": (1 - avg_second/avg_first) * 100
                },
                suggestions=[
                    "立即分析下降原因（市场环境、竞争、产品问题）",
                    "对比同期数据确认是否为季节性波动",
                    "检查营销活动、产品质量、用户体验等关键因素",
                    "分析各维度的数据，定位具体问题区域"
                ]
            )
        elif avg_second > avg_first * 1.1:  # 上升超过10%
            return RootCause(
                cause_type="趋势上升",
                description=f"指标呈上升趋势，前半段平均{avg_first:.2f}，后半段平均{avg_second:.2f}，增长{(avg_second/avg_first-1)*100:.1f}%",
                severity="low",
                confidence=0.8,
                evidence={
                    "first_half_avg": avg_first,
                    "second_half_avg": avg_second,
                    "growth_rate": (avg_second/avg_first - 1) * 100
                },
                suggestions=[
                    "保持当前策略并继续优化",
                    "分析增长因素以便复制到其他指标/渠道",
                    "注意快速增长是否可持续"
                ]
            )

        return None

    def _analyze_related_metrics(
        self,
        metric: str,
        time_range: TimeRange,
        metric_def: Dict[str, Any]
    ) -> Optional[RootCause]:
        """分析相关指标."""
        related = metric_def.get("related_metrics", [])

        if not related:
            return None

        # 检查相关指标的趋势
        issues = []
        for related_metric in related[:3]:
            related_def = registry.get_metric(related_metric)
            if not related_def:
                continue

            mql_query = MQLQuery(
                metric=related_metric,
                time_range=time_range
            )

            result = self.engine.execute(mql_query)
            data = result.get("result", [])

            if data:
                values = [row["value"] for row in data]
                avg = sum(values) / len(values)

                # 检查相关指标是否也有问题
                if "率" in metric_def["unit"] or "%" in metric_def["unit"]:
                    # 对于百分比指标，低于某个值视为问题
                    if avg < 50:  # 例如：转化率低于50%
                        issues.append(f"{related_def['name']}较低（{avg:.2f}%）")

                if issues:
                    return RootCause(
                        cause_type="关联指标异常",
                        description=f"相关指标也表现不佳: {', '.join(issues)}",
                        severity="medium",
                        confidence=0.7,
                        evidence={
                            "related_issues": issues
                        },
                        suggestions=[
                            "综合优化相关指标，系统性地解决问题",
                            "分析指标间的因果关系，找到根本原因",
                            "制定整体改进方案而非单独优化某一指标"
                        ]
                    )

        return None


# 测试
if __name__ == "__main__":
    from datetime import datetime, timedelta

    print("\n🧪 测试根因分析")
    print("=" * 60)

    analyzer = RootCauseAnalyzer()

    # 分析GMV的根因
    time_range = TimeRange(
        start=datetime.now() - timedelta(days=7),
        end=datetime.now(),
        granularity="day"
    )

    print("\n分析: GMV（最近7天）")
    print("-" * 60)

    root_causes = analyzer.analyze(
        metric="GMV",
        time_range=time_range,
        threshold=100000,
        dimensions=["地区", "品类"]
    )

    print(f"\n发现 {len(root_causes)} 个潜在根因:")
    for i, cause in enumerate(root_causes, 1):
        print(f"\n{i}. [{cause.severity.upper()}] {cause.cause_type}")
        print(f"   {cause.description}")
        print(f"   置信度: {cause.confidence}")
        if cause.suggestions:
            print(f"   建议:")
            for j, suggestion in enumerate(cause.suggestions, 1):
                print(f"      {j}. {suggestion}")

    print("\n" + "=" * 60)
