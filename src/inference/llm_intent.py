"""LLM增强的意图识别模块."""

import json
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Optional

import httpx


@dataclass
class LLMIntentResult:
    """LLM意图识别结果."""

    core_query: str
    time_range: Optional[dict[str, str]]
    time_granularity: Optional[str]
    aggregation_type: Optional[str]
    dimensions: list[str]
    comparison_type: Optional[str]
    filters: dict[str, Any]
    confidence: float  # 置信度 0-1
    reasoning: str  # 推理过程
    model: str  # 使用的模型
    latency: float  # 延迟（秒）


class LLMIntentRecognizer:
    """基于LLM的意图识别器."""

    # API配置
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    # 模型选择
    MODEL_FAST = "gpt-4o-mini"  # 快速模型（$0.15/1M input）
    MODEL_ACCURATE = "gpt-4o"  # 准确模型（$2.5/1M input）

    # Few-shot示例
    FEW_SHOT_EXAMPLES = [
        {
            "query": "GMV",
            "intent": {
                "core_query": "GMV",
                "time_range": None,
                "time_granularity": None,
                "aggregation_type": None,
                "dimensions": [],
                "comparison_type": None,
                "filters": {},
                "confidence": 1.0,
                "reasoning": "精确指标查询"
            }
        },
        {
            "query": "最近7天的GMV",
            "intent": {
                "core_query": "GMV",
                "time_range": {
                    "type": "relative",
                    "value": "7d",
                    "start": "2024-01-25",
                    "end": "2024-02-01"
                },
                "time_granularity": "day",
                "aggregation_type": None,
                "dimensions": [],
                "comparison_type": None,
                "filters": {},
                "confidence": 0.98,
                "reasoning": "识别到时间词'最近7天'（相对时间），时间粒度为天，核心指标为GMV"
            }
        },
        {
            "query": "本月营收总和",
            "intent": {
                "core_query": "营收",
                "time_range": {
                    "type": "absolute",
                    "value": "this_month",
                    "start": "2024-02-01",
                    "end": "2024-02-29"
                },
                "time_granularity": "month",
                "aggregation_type": "sum",
                "dimensions": [],
                "comparison_type": None,
                "filters": {"domain": "营收"},
                "confidence": 0.95,
                "reasoning": "识别到时间词'本月'（绝对时间），聚合词'总和'，核心查询为'营收'"
            }
        },
        {
            "query": "按地区的成交金额同比",
            "intent": {
                "core_query": "成交金额",
                "time_range": None,
                "time_granularity": None,
                "aggregation_type": None,
                "dimensions": ["地区"],
                "comparison_type": "yoy",
                "filters": {},
                "confidence": 0.92,
                "reasoning": "识别到维度'按地区'，比较词'同比'（year-over-year），核心查询为'成交金额'（GMV的同义词）"
            }
        },
        {
            "query": "DAU是什么",
            "intent": {
                "core_query": "DAU",
                "time_range": None,
                "time_granularity": None,
                "aggregation_type": None,
                "dimensions": [],
                "comparison_type": None,
                "filters": {},
                "confidence": 0.99,
                "reasoning": "识别到疑问词'是什么'，核心查询为'DAU'，这是一个定义查询"
            }
        },
    ]

    def __init__(self, model: str = MODEL_FAST):
        """初始化LLM意图识别器.

        Args:
            model: 使用的模型名称
        """
        self.model = model
        self.client = None

        if not self.OPENAI_API_KEY:
            print("⚠️  警告: OPENAI_API_KEY 未设置，LLM功能将不可用")
            print("   设置方法: export OPENAI_API_KEY='your-api-key'")

    def _build_prompt(self, query: str) -> str:
        """构建Few-shot提示词.

        Args:
            query: 用户查询

        Returns:
            完整的提示词
        """
        # 构建示例部分
        examples_text = ""
        for i, example in enumerate(self.FEW_SHOT_EXAMPLES[:3], 1):  # 使用前3个示例
            examples_text += f"""
### 示例 {i}
查询: {example['query']}
意图: {json.dumps(example['intent'], ensure_ascii=False, indent=2)}

"""

        # 完整提示词
        prompt = f"""你是一个专业的BI（商业智能）查询意图识别专家。你的任务是分析用户的自然语言查询，提取结构化的意图信息。

## 意图维度说明

请从以下7个维度分析查询：

1. **core_query** (核心查询词): 提取用户真正想查询的指标名称
   - 去除时间词、疑问词、聚合词
   - 识别同义词（如"成交金额" → "GMV"）

2. **time_range** (时间范围): 识别时间范围
   - 相对时间: "最近7天" → {{"type": "relative", "value": "7d", "start": "2024-01-25", "end": "2024-02-01"}}
   - 绝对时间: "本月" → {{"type": "absolute", "value": "this_month", "start": "2024-02-01", "end": "2024-02-29"}}
   - 无时间: null

3. **time_granularity** (时间粒度): day/week/month/quarter/year/realtime

4. **aggregation_type** (聚合类型): sum/avg/count/max/min/rate/ratio

5. **dimensions** (维度列表): 如 ["地区", "品类", "渠道"]

6. **comparison_type** (比较类型): yoy(同比)/mom(环比)/dod(日环比)/wow(周环比)

7. **filters** (过滤条件): 如 {{"domain": "电商"}}

## 输出格式

请严格按照以下JSON格式输出：

```json
{{
    "core_query": "核心指标名",
    "time_range": null or {{"type": "...", "value": "...", "start": "...", "end": "..." }},
    "time_granularity": null or "day|week|month|quarter|year",
    "aggregation_type": null or "sum|avg|count|max|min|rate|ratio",
    "dimensions": [],
    "comparison_type": null or "yoy|mom|dod|wow",
    "filters": {{}},
    "confidence": 0.95,
    "reasoning": "详细的推理过程说明"
}}
```

## Few-Shot示例
{examples_text}
## 待识别查询

查询: {query}

请分析上述查询并输出JSON格式的意图信息：
"""

        return prompt

    async def recognize_async(self, query: str) -> Optional[LLMIntentResult]:
        """异步识别查询意图.

        Args:
            query: 用户查询文本

        Returns:
            LLM意图识别结果，如果API未配置则返回None
        """
        if not self.OPENAI_API_KEY:
            return None

        start_time = time.time()

        try:
            # 构建请求
            prompt = self._build_prompt(query)

            # 调用OpenAI API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.OPENAI_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "你是一个专业的BI查询意图识别专家。严格按照JSON格式输出结果。"
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.1,  # 降低随机性，提高稳定性
                        "max_tokens": 1000,
                        "response_format": {"type": "json_object"}  # 强制JSON输出
                    }
                )

                response.raise_for_status()
                data = response.json()

            # 解析结果
            content = data["choices"][0]["message"]["content"]
            intent_data = json.loads(content)

            # 计算延迟
            latency = time.time() - start_time

            # 构建结果对象
            result = LLMIntentResult(
                core_query=intent_data.get("core_query", ""),
                time_range=intent_data.get("time_range"),
                time_granularity=intent_data.get("time_granularity"),
                aggregation_type=intent_data.get("aggregation_type"),
                dimensions=intent_data.get("dimensions", []),
                comparison_type=intent_data.get("comparison_type"),
                filters=intent_data.get("filters", {}),
                confidence=intent_data.get("confidence", 0.5),
                reasoning=intent_data.get("reasoning", ""),
                model=self.model,
                latency=latency
            )

            return result

        except httpx.HTTPError as e:
            print(f"❌ LLM API请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ LLM返回的JSON解析失败: {e}")
            return None
        except Exception as e:
            print(f"❌ LLM意图识别异常: {e}")
            return None

    def recognize(self, query: str) -> Optional[LLMIntentResult]:
        """同步识别查询意图（包装异步方法）.

        Args:
            query: 用户查询文本

        Returns:
            LLM意图识别结果
        """
        import asyncio

        try:
            # 在新的事件循环中运行异步方法
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.recognize_async(query))
            loop.close()
            return result
        except Exception as e:
            print(f"❌ 同步调用失败: {e}")
            return None


# 本地模型支持（使用Ollama）
class LocalLLMIntentRecognizer:
    """本地LLM意图识别器（使用Ollama）."""

    def __init__(self, model: str = "qwen2.5:7b"):
        """初始化本地LLM识别器.

        Args:
            model: Ollama模型名称
        """
        self.model = model
        self.base_url = "http://localhost:11434"

    def is_available(self) -> bool:
        """检查Ollama服务是否可用."""
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            return response.status_code == 200
        except Exception:
            return False

    def recognize(self, query: str) -> Optional[LLMIntentResult]:
        """使用本地模型识别意图.

        Args:
            query: 用户查询文本

        Returns:
            LLM意图识别结果
        """
        if not self.is_available():
            print("⚠️  Ollama服务未启动")
            return None

        start_time = time.time()

        try:
            import httpx

            # 构建简化的提示词（本地模型上下文窗口较小）
            prompt = f"""分析以下BI查询的意图，输出JSON格式：
查询: {query}

输出格式：
{{
    "core_query": "核心指标",
    "time_range": null,
    "time_granularity": null,
    "aggregation_type": null,
    "dimensions": [],
    "comparison_type": null,
    "filters": {{}},
    "confidence": 0.9,
    "reasoning": "推理过程"
}}

输出JSON："""

            # 调用Ollama API
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 500
                    }
                },
                timeout=60.0
            )

            response.raise_for_status()
            data = response.json()

            # 提取JSON（模型可能输出多余文本）
            content = data.get("response", "")

            # 尝试提取JSON部分
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group()

            intent_data = json.loads(content)

            # 构建结果
            return LLMIntentResult(
                core_query=intent_data.get("core_query", query),
                time_range=intent_data.get("time_range"),
                time_granularity=intent_data.get("time_granularity"),
                aggregation_type=intent_data.get("aggregation_type"),
                dimensions=intent_data.get("dimensions", []),
                comparison_type=intent_data.get("comparison_type"),
                filters=intent_data.get("filters", {}),
                confidence=intent_data.get("confidence", 0.7),
                reasoning=intent_data.get("reasoning", ""),
                model=self.model,
                latency=time.time() - start_time
            )

        except Exception as e:
            print(f"❌ 本地LLM识别失败: {e}")
            return None
