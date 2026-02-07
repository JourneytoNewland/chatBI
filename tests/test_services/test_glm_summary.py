"""GLM 摘要生成服务测试."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.summary_service import GLMSummaryService


class TestGLMSummaryService:
    """GLM 摘要生成服务测试."""

    @pytest.fixture
    def mock_zhipuai_client(self):
        """Mock 智谱 AI 客户端."""
        with patch("src.services.summary_service.ZhipuAI") as mock:
            yield mock

    @pytest.fixture
    def summary_service(self, mock_zhipuai_client):
        """创建摘要服务实例."""
        return GLMSummaryService(api_key="test_api_key")

    @pytest.fixture
    def sample_metadata(self):
        """示例指标元数据."""
        return {
            "name": "GMV",
            "code": "gmv",
            "description": "成交总额（Gross Merchandise Volume）",
            "domain": "电商",
            "formula": "SUM(订单金额)",
            "synonyms": ["成交金额", "交易额", "总交易额"]
        }

    # ========== 正常情况测试 ==========

    def test_generate_summaries_success(self, summary_service, sample_metadata, mock_zhipuai_client):
        """测试成功生成摘要."""
        # Mock GLM 响应
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "business_summary": "GMV是电商平台的核心指标...",
            "llm_friendly_text": "Metric: GMV, Code: gmv, Domain: 电商...",
            "rag_document": "# GMV\\n\\n## 业务定义...",
            "keywords": ["GMV", "成交额", "电商", "交易额", "销售"],
            "example_queries": ["GMV是多少", "查询GMV趋势", "按地区查看GMV"]
        })

        mock_zhipuai_client.return_value.chat.completions.create.return_value = mock_response

        # 执行测试（需要在异步环境中）
        import asyncio

        async def run_test():
            summaries = await summary_service.generate_metric_summaries(sample_metadata)

            assert summaries is not None
            assert "business_summary" in summaries
            assert "llm_friendly_text" in summaries
            assert "rag_document" in summaries
            assert "keywords" in summaries
            assert "example_queries" in summaries
            assert len(summaries["keywords"]) == 5
            assert len(summaries["example_queries"]) == 3

        asyncio.run(run_test())

    def test_generate_summaries_with_context(self, summary_service, sample_metadata, mock_zhipuai_client):
        """测试带上下文的摘要生成."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "business_summary": "根据上下文，GMV是...",
            "llm_friendly_text": "Metric: GMV...",
            "rag_document": "# GMV\\n\\n上下文信息...",
            "keywords": ["GMV"],
            "example_queries": ["GMV是多少"]
        })

        mock_zhipuai_client.return_value.chat.completions.create.return_value = mock_response

        import asyncio

        async def run_test():
            summaries = await summary_service.generate_metric_summaries(
                sample_metadata,
                context="这是季度核心指标"
            )

            assert summaries is not None
            assert "上下文" in summaries["rag_document"]

        asyncio.run(run_test())

    def test_batch_generate_summaries(self, summary_service, mock_zhipuai_client):
        """测试批量生成摘要."""
        metrics = [
            {
                "name": "GMV",
                "code": "gmv",
                "description": "成交总额",
                "domain": "电商",
                "synonyms": ["成交金额"],
                "formula": "SUM(订单金额)"
            },
            {
                "name": "DAU",
                "code": "dau",
                "description": "日活跃用户数",
                "domain": "用户",
                "synonyms": ["日活"],
                "formula": "COUNT(DISTINCT user_id) WHERE date = TODAY"
            }
        ]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "business_summary": "测试摘要",
            "llm_friendly_text": "Metric: Test",
            "rag_document": "# Test",
            "keywords": ["test"],
            "example_queries": ["test"]
        })

        mock_zhipuai_client.return_value.chat.completions.create.return_value = mock_response

        import asyncio

        async def run_test():
            summaries = await summary_service.batch_generate_summaries(
                metrics=metrics,
                batch_size=2,
                show_progress=False
            )

            assert len(summaries) == 2
            assert all("business_summary" in s for s in summaries)

        asyncio.run(run_test())

    # ========== 降级情况测试 ==========

    def test_fallback_summaries_when_llm_fails(self, summary_service, sample_metadata, mock_zhipuai_client):
        """测试 LLM 调用失败时使用默认摘要."""
        # Mock LLM 调用失败
        mock_zhipuai_client.return_value.chat.completions.create.side_effect = Exception("API Error")

        import asyncio

        async def run_test():
            summaries = await summary_service.generate_metric_summaries(sample_metadata)

            # 验证降级到默认摘要
            assert summaries is not None
            assert "business_summary" in summaries
            assert "GMV" in summaries["business_summary"]
            assert "电商" in summaries["business_summary"]

        asyncio.run(run_test())

    def test_fallback_summaries_when_invalid_json(self, summary_service, sample_metadata, mock_zhipuai_client):
        """测试 LLM 返回无效 JSON 时使用默认摘要."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "这不是有效的 JSON"

        mock_zhipuai_client.return_value.chat.completions.create.return_value = mock_response

        import asyncio

        async def run_test():
            summaries = await summary_service.generate_metric_summaries(sample_metadata)

            # 验证降级到默认摘要
            assert summaries is not None
            assert "business_summary" in summaries

        asyncio.run(run_test())

    # ========== 边界情况测试 ==========

    def test_empty_metadata(self, summary_service, mock_zhipuai_client):
        """测试空元数据."""
        mock_zhipuai_client.return_value.chat.completions.create.side_effect = Exception("No Data")

        import asyncio

        async def run_test():
            summaries = await summary_service.generate_metric_summaries({})

            # 验证使用默认值
            assert summaries is not None
            assert "business_summary" in summaries

        asyncio.run(run_test())

    def test_metadata_with_missing_fields(self, summary_service, mock_zhipuai_client):
        """测试缺少字段的元数据."""
        incomplete_metadata = {
            "name": "Test Metric",
            "code": "test"
        }

        mock_zhipuai_client.return_value.chat.completions.create.side_effect = Exception("Incomplete Data")

        import asyncio

        async def run_test():
            summaries = await summary_service.generate_metric_summaries(incomplete_metadata)

            assert summaries is not None
            assert "Test Metric" in summaries["business_summary"]

        asyncio.run(run_test())

    def test_batch_with_empty_list(self, summary_service):
        """测试批量处理空列表."""
        import asyncio

        async def run_test():
            summaries = await summary_service.batch_generate_summaries([])

            assert summaries == []

        asyncio.run(run_test())

    # ========== 性能测试 ==========

    def test_batch_performance(self, summary_service, mock_zhipuai_client):
        """测试批量处理性能."""
        # 创建 10 个指标
        metrics = [
            {
                "name": f"Metric{i}",
                "code": f"metric{i}",
                "description": f"测试指标{i}",
                "domain": "测试",
                "synonyms": [],
                "formula": "N/A"
            }
            for i in range(10)
        ]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "business_summary": "测试",
            "llm_friendly_text": "Metric: Test",
            "rag_document": "# Test",
            "keywords": ["test"],
            "example_queries": ["test"]
        })

        mock_zhipuai_client.return_value.chat.completions.create.return_value = mock_response

        import asyncio
        import time

        async def run_test():
            start = time.time()
            summaries = await summary_service.batch_generate_summaries(
                metrics=metrics,
                batch_size=5,
                show_progress=False
            )
            elapsed = time.time() - start

            assert len(summaries) == 10
            # 批处理应该比串行快（这里只是验证不会超时）
            assert elapsed < 10  # 不应该超过10秒

        asyncio.run(run_test())


class TestPromptBuilding:
    """提示词构建测试."""

    @pytest.fixture
    def summary_service(self):
        """创建摘要服务实例."""
        with patch("src.services.summary_service.ZhipuAI"):
            return GLMSummaryService(api_key="test_key")

    def test_build_prompt_with_all_fields(self, summary_service):
        """测试构建完整提示词."""
        metadata = {
            "name": "GMV",
            "code": "gmv",
            "description": "成交总额",
            "domain": "电商",
            "formula": "SUM(订单金额)",
            "synonyms": ["成交金额", "交易额"]
        }

        prompt = summary_service._build_summary_prompt(metadata, None)

        assert "GMV" in prompt
        assert "gmv" in prompt
        assert "成交总额" in prompt
        assert "电商" in prompt
        assert "SUM(订单金额)" in prompt
        assert "成交金额" in prompt
        assert "business_summary" in prompt
        assert "llm_friendly_text" in prompt
        assert "rag_document" in prompt

    def test_build_prompt_with_context(self, summary_service):
        """测试带上下文的提示词."""
        metadata = {"name": "GMV", "code": "gmv", "description": "成交总额", "domain": "电商"}

        prompt = summary_service._build_summary_prompt(metadata, "这是季度核心指标")

        assert "GMV" in prompt
        assert "上下文信息" in prompt
        assert "季度核心指标" in prompt

    def test_build_prompt_with_minimal_fields(self, summary_service):
        """测试最小字段的提示词."""
        metadata = {
            "name": "GMV",
            "code": "gmv",
            "description": "成交总额",
            "domain": "电商"
        }

        prompt = summary_service._build_summary_prompt(metadata, None)

        # 应该包含基本信息，但显示"无"的占位符
        assert "GMV" in prompt
        assert "无" in prompt  # formula 和 synonyms 缺失时显示"无"


class TestFallbackSummaries:
    """默认摘要测试."""

    @pytest.fixture
    def summary_service(self):
        """创建摘要服务实例."""
        with patch("src.services.summary_service.ZhipuAI"):
            return GLMSummaryService(api_key="test_key")

    def test_fallback_structure(self, summary_service):
        """测试默认摘要结构."""
        metadata = {
            "name": "GMV",
            "code": "gmv",
            "description": "成交总额",
            "domain": "电商",
            "synonyms": ["成交金额"],
            "formula": "SUM(订单金额)"
        }

        fallback = summary_service._fallback_summaries(metadata)

        assert "business_summary" in fallback
        assert "llm_friendly_text" in fallback
        assert "rag_document" in fallback
        assert "keywords" in fallback
        assert "example_queries" in fallback

        # 验证内容包含关键词
        assert "GMV" in fallback["business_summary"]
        assert "电商" in fallback["business_summary"]
        assert "SUM(订单金额)" in fallback["business_summary"]

    def test_fallback_keywords_generation(self, summary_service):
        """测试关键词生成."""
        metadata = {
            "name": "GMV",
            "code": "gmv",
            "description": "成交总额",
            "domain": "电商",
            "synonyms": ["成交金额", "交易额", "总交易额", "销售金额", "营业额"],
            "formula": "SUM(订单金额)"
        }

        fallback = summary_service._fallback_summaries(metadata)

        # 关键词应该包含：name, code, domain + 前3个同义词
        assert len(fallback["keywords"]) <= 6  # name + code + domain + 3个同义词
        assert "GMV" in fallback["keywords"]
        assert "gmv" in fallback["keywords"]
        assert "电商" in fallback["keywords"]

    def test_fallback_example_queries(self, summary_service):
        """测试示例查询生成."""
        metadata = {
            "name": "GMV",
            "code": "gmv",
            "description": "成交总额",
            "domain": "电商",
            "synonyms": [],
            "formula": "SUM(订单金额)"
        }

        fallback = summary_service._fallback_summaries(metadata)

        assert len(fallback["example_queries"]) == 3
        assert any("GMV" in q for q in fallback["example_queries"])
        assert any("趋势" in q for q in fallback["example_queries"])
        assert any("电商" in q for q in fallback["example_queries"])
