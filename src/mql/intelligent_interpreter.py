"""智能解读模块 - 基于查询结果生成分析报告."""

import json
import logging
import statistics
from typing import Any, Dict, List, Optional

from .models import InterpretationResult, DataAnalysisResult

logger = logging.getLogger(__name__)


class IntelligentInterpreter:
    """智能解读器.

    功能:
    1. 数据分析（趋势、波动、异常检测）
    2. LLM解读生成（总结、发现、洞察、建议）
    3. 降级机制（LLM失败时使用模板）

    Attributes:
        llm_model: 使用的LLM模型名称
    """

    def __init__(self, llm_model: str = "glm-4-flash") -> None:
        """初始化智能解读器.

        Args:
            llm_model: LLM模型名称（默认使用glm-4-flash）
        """
        self.llm_model = llm_model

    def interpret(
        self,
        query: str,
        mql_result: Dict[str, Any],
        metric_def: Dict[str, Any]
    ) -> InterpretationResult:
        """智能解读查询结果.

        Args:
            query: 用户原始查询
            mql_result: MQL执行结果
            metric_def: 指标定义

        Returns:
            InterpretationResult: 智能解读结果
        """
        # 1. 数据分析
        data_analysis = self._analyze_data(mql_result["result"])

        # 2. 尝试LLM解读
        try:
            # 构建提示词（保存用于展示）
            prompt = self._build_llm_prompt(query, data_analysis, metric_def, mql_result)

            # 保存提示词到data_analysis中，供前端展示
            data_analysis["_prompt"] = prompt

            interpretation = self._generate_llm_interpretation(
                query,
                data_analysis,
                metric_def,
                mql_result
            )

            # 计算置信度
            confidence = self._calculate_confidence(data_analysis, interpretation)

            return InterpretationResult(
                summary=interpretation.get("summary", self._generate_default_summary(data_analysis, metric_def)),
                trend=data_analysis["trend"],
                key_findings=interpretation.get("key_findings", self._generate_default_findings(data_analysis)),
                insights=interpretation.get("insights", self._generate_default_insights(data_analysis, metric_def)),
                suggestions=interpretation.get("suggestions", self._generate_default_suggestions(data_analysis)),
                confidence=confidence,
                data_analysis=data_analysis
            )

        except Exception as e:
            logger.warning(f"LLM解读失败，使用模板生成: {e}")

            # 3. 降级到模板生成
            return self._generate_template_interpretation(
                query,
                data_analysis,
                metric_def,
                mql_result
            )

    def _analyze_data(self, data: List[Dict]) -> Dict[str, Any]:
        """分析数据特征.

        Args:
            data: 查询结果数据

        Returns:
            数据分析结果字典
        """
        if len(data) < 2:
            return {
                "trend": "stable",
                "change_rate": 0,
                "volatility": 0,
                "anomalies": [],
                "min": data[0]["value"] if data else 0,
                "max": data[0]["value"] if data else 0,
                "avg": data[0]["value"] if data else 0,
                "std": 0
            }

        values = [row["value"] for row in data]

        # 计算变化率
        first_val = values[0]
        last_val = values[-1]
        change_rate = (last_val - first_val) / first_val * 100 if first_val != 0 else 0

        # 判断趋势
        if change_rate > 10:
            trend = "upward"
        elif change_rate < -10:
            trend = "downward"
        elif abs(change_rate) < 5:
            trend = "stable"
        else:
            trend = "fluctuating"

        # 计算统计量
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values) if len(values) > 1 else 0
        volatility = (std_val / mean_val * 100) if mean_val != 0 else 0

        # 识别异常值（超过2个标准差）
        anomalies = []
        if len(values) > 3:
            for i, v in enumerate(values):
                if abs(v - mean_val) > 2 * std_val:
                    anomalies.append(i)

        return {
            "trend": trend,
            "change_rate": round(change_rate, 2),
            "volatility": round(volatility, 2),
            "anomalies": anomalies,
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "avg": round(mean_val, 2),
            "std": round(std_val, 2)
        }

    def _generate_llm_interpretation(
        self,
        query: str,
        data_analysis: Dict,
        metric_def: Dict,
        mql_result: Dict
    ) -> Dict[str, Any]:
        """基于LLM生成智能解读.

        Args:
            query: 用户查询
            data_analysis: 数据分析结果
            metric_def: 指标定义
            mql_result: MQL执行结果

        Returns:
            LLM生成的解读字典

        Raises:
            RuntimeError: LLM调用失败时抛出
        """
        try:
            from ..inference.zhipu_intent import ZhipuIntentRecognizer

            # 构建提示词
            prompt = self._build_llm_prompt(query, data_analysis, metric_def, mql_result)

            # 调用ZhipuAI
            llm = ZhipuIntentRecognizer(model=self.llm_model)
            response = llm._call_api(prompt)

            # 解析JSON响应
            interpretation = json.loads(response)
            return interpretation

        except ImportError:
            raise RuntimeError("ZhipuAI SDK未安装")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"LLM返回的不是有效JSON: {e}")
        except Exception as e:
            raise RuntimeError(f"LLM调用失败: {e}")

    def _build_llm_prompt(
        self,
        query: str,
        data_analysis: Dict,
        metric_def: Dict,
        mql_result: Dict
    ) -> str:
        """构建LLM提示词.

        Args:
            query: 用户查询
            data_analysis: 数据分析结果
            metric_def: 指标定义
            mql_result: MQL执行结果

        Returns:
            LLM提示词字符串
        """
        trend_label = {
            "upward": "上升 ↗",
            "downward": "下降 ↘",
            "fluctuating": "波动 〰",
            "stable": "稳定 →"
        }.get(data_analysis["trend"], "未知")

        return f"""你是一个专业的数据分析助手。请基于以下查询结果生成智能解读：

## 用户查询
{query}

## 指标信息
- 指标名称：{metric_def.get('name', '未知')}
- 指标定义：{metric_def.get('description', '无描述')}
- 单位：{metric_def.get('unit', '')}

## 数据分析结果
- 趋势：{trend_label}
- 变化率：{data_analysis['change_rate']:.2f}%
- 波动性：{data_analysis['volatility']:.2f}%
- 最小值：{data_analysis['min']}
- 最大值：{data_analysis['max']}
- 平均值：{data_analysis['avg']:.2f}

## 查询结果（前5条）
{self._format_results(mql_result['result'][:5])}

请生成：
1. **summary**（总结，2-3句话）：概括主要发现
2. **key_findings**（关键发现，3-5点）：数据中的重要特征
3. **insights**（深入洞察，2-3点）：背后的原因分析
4. **suggestions**（行动建议，2-3点）：基于数据的建议

请以JSON格式返回（不要使用markdown代码块，直接返回JSON）：
{{
    "summary": "...",
    "key_findings": ["...", "...", "..."],
    "insights": ["...", "..."],
    "suggestions": ["...", "..."]
}}
"""

    def _format_results(self, results: List[Dict]) -> str:
        """格式化查询结果用于提示词.

        Args:
            results: 查询结果列表

        Returns:
            格式化的字符串
        """
        if not results:
            return "无数据"

        lines = []
        for i, row in enumerate(results, 1):
            date = row.get("date", "未知日期")
            value = row.get("value", 0)
            lines.append(f"{i}. {date}: {value}")

        return "\n".join(lines)

    def _calculate_confidence(
        self,
        data_analysis: Dict,
        interpretation: Dict
    ) -> float:
        """计算解读置信度.

        Args:
            data_analysis: 数据分析结果
            interpretation: LLM解读结果

        Returns:
            置信度（0-1）
        """
        confidence = 0.5  # 基础置信度

        # 1. 数据量影响置信度
        if "data_count" in data_analysis:
            if data_analysis["data_count"] >= 7:
                confidence += 0.2
            elif data_analysis["data_count"] >= 3:
                confidence += 0.1

        # 2. 波动性影响置信度（波动过大降低置信度）
        if data_analysis.get("volatility", 0) < 20:
            confidence += 0.15
        elif data_analysis.get("volatility", 0) > 50:
            confidence -= 0.15

        # 3. 趋势明确性影响置信度
        if data_analysis.get("trend") in ["upward", "downward"]:
            confidence += 0.1

        # 4. 解读完整性影响置信度
        if interpretation.get("summary"):
            confidence += 0.05
        if interpretation.get("key_findings") and len(interpretation["key_findings"]) >= 3:
            confidence += 0.1
        if interpretation.get("insights") and len(interpretation["insights"]) >= 2:
            confidence += 0.1
        if interpretation.get("suggestions") and len(interpretation["suggestions"]) >= 2:
            confidence += 0.1

        # 确保置信度在0-1之间
        return max(0.0, min(1.0, confidence))

    def _generate_template_interpretation(
        self,
        query: str,
        data_analysis: Dict,
        metric_def: Dict,
        mql_result: Dict
    ) -> InterpretationResult:
        """生成模板解读（降级方案）.

        Args:
            query: 用户查询
            data_analysis: 数据分析结果
            metric_def: 指标定义
            mql_result: MQL执行结果

        Returns:
            InterpretationResult: 模板解读结果
        """
        return InterpretationResult(
            summary=self._generate_default_summary(data_analysis, metric_def),
            trend=data_analysis["trend"],
            key_findings=self._generate_default_findings(data_analysis),
            insights=self._generate_default_insights(data_analysis, metric_def),
            suggestions=self._generate_default_suggestions(data_analysis),
            confidence=0.6,  # 模板解读置信度较低
            data_analysis=data_analysis
        )

    def _generate_default_summary(self, data_analysis: Dict, metric_def: Dict) -> str:
        """生成默认总结.

        Args:
            data_analysis: 数据分析结果
            metric_def: 指标定义

        Returns:
            总结字符串
        """
        metric_name = metric_def.get("name", "指标")
        change_rate = data_analysis["change_rate"]

        trend_desc = {
            "upward": "呈上升趋势",
            "downward": "呈下降趋势",
            "fluctuating": "呈波动状态",
            "stable": "保持稳定"
        }.get(data_analysis["trend"], "变化")

        if abs(change_rate) > 0:
            return f"{metric_name}{trend_desc}，变化率为{change_rate:.2f}%。"
        else:
            return f"{metric_name}{trend_desc}。"

    def _generate_default_findings(self, data_analysis: Dict) -> List[str]:
        """生成默认关键发现.

        Args:
            data_analysis: 数据分析结果

        Returns:
            关键发现列表
        """
        findings = []

        # 趋势发现
        trend_desc = {
            "upward": "数据呈上升趋势",
            "downward": "数据呈下降趋势",
            "fluctuating": "数据波动较大",
            "stable": "数据保持稳定"
        }.get(data_analysis["trend"], "数据变化")

        findings.append(trend_desc)

        # 变化率发现
        if abs(data_analysis["change_rate"]) > 10:
            findings.append(f"总体变化率达到{data_analysis['change_rate']:.2f}%")

        # 波动性发现
        if data_analysis["volatility"] < 10:
            findings.append("波动性较低，数据稳定")
        elif data_analysis["volatility"] > 30:
            findings.append(f"波动性较高（{data_analysis['volatility']:.2f}%），需关注异常")

        # 极值发现
        findings.append(f"最小值{data_analysis['min']}，最大值{data_analysis['max']}")

        # 异常值发现
        if data_analysis.get("anomalies"):
            findings.append(f"检测到{len(data_analysis['anomalies'])}个异常值点")

        return findings[:5]  # 最多返回5条

    def _generate_default_insights(
        self,
        data_analysis: Dict,
        metric_def: Dict
    ) -> List[str]:
        """生成默认深入洞察.

        Args:
            data_analysis: 数据分析结果
            metric_def: 指标定义

        Returns:
            深入洞察列表
        """
        insights = []

        # 基于趋势的洞察
        if data_analysis["trend"] == "upward":
            insights.append("持续增长可能反映出业务扩张或季节性需求增加")
        elif data_analysis["trend"] == "downward":
            insights.append("下降趋势可能与市场竞争加剧或需求减少有关")
        elif data_analysis["trend"] == "fluctuating":
            insights.append("波动可能受周期性因素或促销活动影响")

        # 基于波动性的洞察
        if data_analysis["volatility"] > 30:
            insights.append("高波动性表明存在不稳定因素，建议深入分析原因")

        # 基于异常值的洞察
        if data_analysis.get("anomalies"):
            insights.append("异常值可能代表特殊事件或数据质量问题，需进一步核实")

        return insights[:3]  # 最多返回3条

    def _generate_default_suggestions(self, data_analysis: Dict) -> List[str]:
        """生成默认行动建议.

        Args:
            data_analysis: 数据分析结果

        Returns:
            行动建议列表
        """
        suggestions = []

        # 基于趋势的建议
        if data_analysis["trend"] == "upward":
            suggestions.append("建议保持当前策略，同时监控增长可持续性")
        elif data_analysis["trend"] == "downward":
            suggestions.append("建议分析下降原因，考虑调整策略或采取改进措施")
        elif data_analysis["trend"] == "fluctuating":
            suggestions.append("建议加强数据分析，识别并消除波动因素")

        # 基于异常值的建议
        if data_analysis.get("anomalies"):
            suggestions.append("建议调查异常值原因，确保数据准确性")

        # 基于波动性的建议
        if data_analysis["volatility"] > 30:
            suggestions.append("建议实施风险控制措施，降低波动性")

        return suggestions[:3]  # 最多返回3条


# 测试
if __name__ == "__main__":
    print("\n🧪 测试智能解读器")
    print("=" * 60)

    interpreter = IntelligentInterpreter()

    # 模拟查询结果
    from datetime import datetime, timedelta

    mock_data = []
    for i in range(7):
        mock_data.append({
            "date": (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d"),
            "value": 500000 + i * 20000 + (i % 2) * 10000,  # 模拟上升趋势
            "metric": "GMV",
            "unit": "元"
        })

    metric_def = {
        "name": "GMV",
        "description": "商品交易总额",
        "unit": "元"
    }

    mql_result = {
        "result": mock_data,
        "row_count": len(mock_data)
    }

    # 测试解读
    print("\n测试查询: 最近7天GMV")
    print("-" * 60)

    interpretation = interpreter.interpret(
        query="最近7天GMV",
        mql_result=mql_result,
        metric_def=metric_def
    )

    print(f"\n✅ 解读结果:")
    print(f"总结: {interpretation.summary}")
    print(f"趋势: {interpretation.trend}")
    print(f"置信度: {interpretation.confidence:.2f}")
    print(f"\n关键发现:")
    for finding in interpretation.key_findings:
        print(f"  - {finding}")
    print(f"\n深入洞察:")
    for insight in interpretation.insights:
        print(f"  - {insight}")
    print(f"\n行动建议:")
    for suggestion in interpretation.suggestions:
        print(f"  - {suggestion}")

    print("\n" + "=" * 60)
