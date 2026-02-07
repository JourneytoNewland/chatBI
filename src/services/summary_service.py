"""基于 GLM 的摘要生成服务."""

import asyncio
import json
from typing import Any, Dict, List, Optional

from zhipuai import ZhipuAI


class GLMSummaryService:
    """使用智谱 GLM 生成指标摘要.

    支持多种摘要类型：
    - business_summary: 业务摘要（给人类看）
    - llm_friendly_text: LLM友好文本（给向量库用）
    - rag_document: RAG文档结构（给知识库用）
    """

    def __init__(self, api_key: str):
        """初始化 GLM 服务.

        Args:
            api_key: 智谱 API Key
        """
        self.client = ZhipuAI(api_key=api_key)
        self.model = "glm-4-flash"  # 或使用 glm-4-plus、glm-4-air

    async def generate_metric_summaries(
        self,
        metadata: Dict[str, Any],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成指标的多维度摘要.

        Args:
            metadata: 指标元数据
            context: 额外上下文信息

        Returns:
            {
                "business_summary": "业务摘要",
                "llm_friendly_text": "LLM检索文本",
                "rag_document": "RAG文档",
                "keywords": ["关键词列表"],
                "example_queries": ["示例查询"]
            }
        """
        prompt = self._build_summary_prompt(metadata, context)

        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的数据分析专家，擅长将指标元数据转换为不同形式的描述。"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # 降低温度以获得更稳定的结果
                top_p=0.7,
                stream=False,
            )

            result_text = response.choices[0].message.content

            # 解析 JSON 结果
            try:
                summaries = json.loads(result_text)
            except json.JSONDecodeError:
                # 如果 LLM 返回的不是 JSON，构建默认结构
                summaries = self._fallback_summaries(metadata)

            return summaries

        except Exception as e:
            print(f"GLM 摘要生成失败: {e}")
            # 返回默认摘要
            return self._fallback_summaries(metadata)

    def _build_summary_prompt(self, metadata: Dict[str, Any], context: Optional[str]) -> str:
        """构建摘要生成提示词."""
        context_section = f"\n上下文信息：{context}" if context else ""

        prompt = f"""
请为以下指标元数据生成三种不同形式的描述：

**指标元数据：**
- 指标名称：{metadata.get('name', '')}
- 指标编码：{metadata.get('code', '')}
- 业务域：{metadata.get('domain', '')}
- 业务含义：{metadata.get('description', '')}
- 计算公式：{metadata.get('formula', '无')}
- 同义词：{', '.join(metadata.get('synonyms', []))}
{context_section}

请按要求生成并以 JSON 格式返回：

{{
  "business_summary": "业务摘要：3-5句话的简明扼要的业务说明，适合业务人员阅读。突出指标的核心价值和应用场景。",
  "llm_friendly_text": "LLM检索文本：结构化、关键词丰富，便于大模型语义理解。包含指标名称、编码、业务域、核心关键词、同义词。",
  "rag_document": "RAG文档：Markdown 格式，结构化文档。包含标题、业务定义、计算方法、业务应用、同义词参考等章节。",
  "keywords": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"],
  "example_queries": ["示例查询1", "示例查询2", "示例查询3"]
}}
"""
        return prompt.strip()

    def _fallback_summaries(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """生成默认摘要（当 LLM 调用失败时）."""
        name = metadata.get('name', '')
        description = metadata.get('description', '')
        domain = metadata.get('domain', '')
        code = metadata.get('code', '')
        synonyms = metadata.get('synonyms', [])
        formula = metadata.get('formula', '无')

        return {
            "business_summary": f"{name}是{domain}域的核心指标，用于{description}。计算公式为：{formula}。",
            "llm_friendly_text": f"Metric: {name}, Code: {code}, Domain: {domain}, Description: {description}. Also known as: {', '.join(synonyms)}.",
            "rag_document": f"""# {name}（{code}）

## 业务定义
{description}

## 计算方法
{formula}

## 业务应用
该指标属于{domain}域，是评估{domain}业务的关键指标。

## 同义词参考
{', '.join(synonyms)}

## 数据来源
{domain}数据仓库
""",
            "keywords": [name, code, domain] + synonyms[:3],
            "example_queries": [f"{name}是多少", f"查询{name}趋势", f"按{domain}查看{name}"]
        }

    async def batch_generate_summaries(
        self,
        metrics: List[Dict[str, Any]],
        batch_size: int = 5,
        show_progress: bool = True
    ) -> List[Dict[str, Any]]:
        """批量生成摘要.

        Args:
            metrics: 指标元数据列表
            batch_size: 批处理大小（控制并发数）
            show_progress: 是否显示进度

        Returns:
            摘要列表
        """
        summaries = []

        for i in range(0, len(metrics), batch_size):
            batch = metrics[i:i + batch_size]

            # 并发生成当前批次的摘要
            batch_tasks = [
                self.generate_metric_summaries(metric)
                for metric in batch
            ]

            if show_progress:
                print(f"正在生成摘要：{i+1}-{min(i+batch_size, len(metrics))}/{len(metrics)}")

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # 处理结果
            for result in batch_results:
                if isinstance(result, Exception):
                    print(f"摘要生成失败: {result}")
                    # 使用默认摘要
                    summaries.append(self._fallback_summaries({}))
                else:
                    summaries.append(result)

        return summaries
