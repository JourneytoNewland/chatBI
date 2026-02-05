"""智能解读器单元测试."""

import pytest
from datetime import datetime, timedelta
from src.mql.intelligent_interpreter import IntelligentInterpreter
from src.mql.models import InterpretationResult


class TestIntelligentInterpreter:
    """智能解读器测试."""

    def test_initialization(self):
        """测试初始化."""
        interpreter = IntelligentInterpreter()
        assert interpreter.llm_model == "glm-4-flash"

    def test_interpret_upward_trend(self):
        """测试上升趋势解读."""
        interpreter = IntelligentInterpreter()

        # 生成上升趋势的模拟数据
        mock_data = []
        for i in range(7):
            mock_data.append({
                "date": (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d"),
                "value": 500000 + i * 30000,  # 上升趋势
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

        # 执行解读
        interpretation = interpreter.interpret(
            query="最近7天GMV",
            mql_result=mql_result,
            metric_def=metric_def
        )

        # 验证结果
        assert isinstance(interpretation, InterpretationResult)
        assert interpretation.trend == "upward"
        assert interpretation.summary is not None
        assert len(interpretation.key_findings) > 0
        assert len(interpretation.insights) > 0
        assert len(interpretation.suggestions) > 0
        assert 0 <= interpretation.confidence <= 1
        assert interpretation.data_analysis is not None
        assert interpretation.data_analysis["trend"] == "upward"

    def test_interpret_downward_trend(self):
        """测试下降趋势解读."""
        interpreter = IntelligentInterpreter()

        # 生成下降趋势的模拟数据
        mock_data = []
        for i in range(7):
            mock_data.append({
                "date": (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d"),
                "value": 600000 - i * 30000,  # 下降趋势
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

        # 执行解读
        interpretation = interpreter.interpret(
            query="最近7天GMV",
            mql_result=mql_result,
            metric_def=metric_def
        )

        # 验证趋势
        assert interpretation.trend == "downward"

    def test_interpret_stable_trend(self):
        """测试稳定趋势解读."""
        interpreter = IntelligentInterpreter()

        # 生成稳定数据
        base_value = 500000
        mock_data = []
        for i in range(7):
            mock_data.append({
                "date": (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d"),
                "value": base_value + (i % 2) * 1000,  # 小幅波动
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

        # 执行解读
        interpretation = interpreter.interpret(
            query="最近7天GMV",
            mql_result=mql_result,
            metric_def=metric_def
        )

        # 验证趋势
        assert interpretation.trend == "stable"

    def test_analyze_data_with_insufficient_points(self):
        """测试数据点不足时的分析."""
        interpreter = IntelligentInterpreter()

        mock_data = [{"value": 500000}]
        analysis = interpreter._analyze_data(mock_data)

        assert analysis["trend"] == "stable"
        assert analysis["change_rate"] == 0
        assert analysis["avg"] == 500000

    def test_template_interpretation_fallback(self):
        """测试模板解读降级机制."""
        interpreter = IntelligentInterpreter()

        # 生成模拟数据
        mock_data = []
        for i in range(7):
            mock_data.append({
                "date": (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d"),
                "value": 500000 + i * 20000,
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

        # 使用模板解读
        interpretation = interpreter._generate_template_interpretation(
            query="最近7天GMV",
            data_analysis=interpreter._analyze_data(mock_data),
            metric_def=metric_def,
            mql_result=mql_result
        )

        # 验证模板解读结果
        assert isinstance(interpretation, InterpretationResult)
        assert interpretation.summary is not None
        assert len(interpretation.key_findings) > 0
        assert len(interpretation.insights) > 0
        assert len(interpretation.suggestions) > 0
        assert interpretation.confidence < 0.8  # 模板解读置信度较低


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
