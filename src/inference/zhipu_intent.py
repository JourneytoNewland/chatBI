"""智谱AI GLM意图识别模块."""

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import httpx


@dataclass
class ZhipuIntentResult:
    """智谱意图识别结果."""

    core_query: str
    time_range: Optional[dict[str, str]]
    time_granularity: Optional[str]
    aggregation_type: Optional[str]
    dimensions: list[str]
    comparison_type: Optional[str]
    filters: dict[str, Any]
    confidence: float
    reasoning: str
    model: str
    latency: float
    tokens_used: dict[str, int]


class ZhipuIntentRecognizer:
    """基于智谱AI GLM的意图识别器.

    优势:
    - 国产模型，无需VPN
    - 价格优惠（¥1/1M tokens）
    - 支持中文优化
    - 高速率限制（TPM/RPM高）
    """

    # API配置 - 从环境变量读取，不使用硬编码密钥
    API_KEY = os.getenv("ZHIPUAI_API_KEY")
    if not API_KEY:
        raise ValueError("ZHIPUAI_API_KEY environment variable is required")
    BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

    # 模型选择
    MODEL_FAST = "glm-4-flash"  # 快速模型，免费
    MODEL_STANDARD = "glm-4-plus"  # 标准模型
    MODEL_PREMIUM = "glm-4-0520"  # 最新模型

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
                "reasoning": "精确指标名称查询"
            }
        },
        {
            "query": "最近7天的GMV",
            "intent": {
                "core_query": "GMV",
                "time_range": {
                    "type": "relative",
                    "value": "7d",
                    "description": "最近7天"
                },
                "time_granularity": "day",
                "aggregation_type": None,
                "dimensions": [],
                "comparison_type": None,
                "filters": {},
                "confidence": 0.98,
                "reasoning": "识别到时间词'最近7天'（相对时间），核心指标为GMV"
            }
        },
        {
            "query": "本月按渠道统计DAU",
            "intent": {
                "core_query": "DAU",
                "time_range": {
                    "type": "absolute",
                    "value": "this_month",
                    "description": "本月"
                },
                "time_granularity": "month",
                "aggregation_type": None,
                "dimensions": ["渠道"],
                "comparison_type": None,
                "filters": {},
                "confidence": 0.95,
                "reasoning": "识别到时间词'本月'，维度词'按渠道'提取为dimensions=['渠道']，核心指标为'DAU'（去除'按渠道统计'）"
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
                "reasoning": "识别到维度'按地区'，比较词'同比'（year-over-year），核心查询'成交金额'是GMV的同义词"
            }
        },
        {
            "query": "2024年1月的订单转化率",
            "intent": {
                "core_query": "conversion_rate",
                "time_range": {
                    "type": "absolute",
                    "value": "2024-01",
                    "description": "2024年1月"
                },
                "time_granularity": "month",
                "aggregation_type": None,
                "dimensions": [],
                "comparison_type": None,
                "filters": {},
                "confidence": 0.93,
                "reasoning": "识别到精确时间'2024年1月'，核心查询'订单转化率'映射到conversion_rate指标"
            }
        },
    ]

    def __init__(self, model: str = MODEL_FAST):
        """初始化智谱意图识别器.

        Args:
            model: 使用的模型名称
        """
        self.model = model
        self.api_key = self.API_KEY

        if not self.api_key:
            print("⚠️  警告: ZHIPUAI_API_KEY 未设置")
            print("   设置方法: export ZHIPUAI_API_KEY='your-api-key'")

    def _build_prompt(self, query: str, candidates: list = None) -> str:
        """构建Few-shot提示词."""
        examples_text = ""
        for i, example in enumerate(self.FEW_SHOT_EXAMPLES[:4], 1):
            examples_text += f"""
### 示例 {i}
查询: {example['query']}
意图: {json.dumps(example['intent'], ensure_ascii=False, indent=2)}

"""

        # 添加可用指标列表
        candidates_info = ""
        if candidates:
            candidate_names = [c.get('name', c.get('metric_id', '')) for c in candidates[:20]]
            candidates_info = f"""
## 可用指标列表
{json.dumps(candidate_names, ensure_ascii=False, indent=2)}

重要：core_query 必须从上述指标列表中选择！如果查询词不在列表中，请选择最相似的指标。
"""

        prompt = f"""你是一个专业的BI（商业智能）查询意图识别专家。你的任务是分析用户的自然语言查询，提取结构化的意图信息。

## 核心规则

1. **core_query提取**（最重要）：
   - 去除时间词：最近、本月、2024年1月、本周等
   - 去除维度前缀：按XX统计、按XX分析、按XX查看、按XX看 → 提取"XX"到dimensions，剩余部分为core_query
   - 去除统计词：统计、分析、查看、展示、显示等
   - 去除疑问词：是什么、多少、如何等
   - 保留核心指标名称（必须从可用指标列表选择）
   - 同义词映射：成交金额→GMV、成交总额→GMV、订单转化率→conversion_rate

2. **维度提取**：
   - "按渠道统计"、"按渠道分析"、"按渠道查看" → dimensions=["渠道"]
   - "按地区"、"按品类"、"按用户等级" → dimensions提取对应维度
   - 关键示例：
     * "本月按渠道统计DAU" → core_query="DAU", dimensions=["渠道"]
     * "按地区的成交金额" → core_query="GMV", dimensions=["地区"]

3. **聚合词识别**：
   - "总和"、"总计"、"合计" → aggregation_type="sum"
   - "平均"、"均值"、"平均数" → aggregation_type="avg"
   - "统计"、"分析"、"查看"（无明确聚合词） → aggregation_type=null

4. **同义词映射**：
   - "成交金额"、"交易额"、"成交总额"、"销售额"、"流水" → GMV
   - "订单转化率"、"转化率"、"转化比率" → conversion_rate
   - "日活用户"、"每日活跃用户" → DAU

## 意图维度说明

请从以下7个维度分析查询：

1. **core_query**: 核心指标名（必须从可用指标列表选择）
2. **time_range**: 时间范围（相对时间或绝对时间）
3. **time_granularity**: day/week/month/quarter/year
4. **aggregation_type**: sum/avg/count/max/min/rate/ratio
5. **dimensions**: 维度列表，如["地区", "品类"]
6. **comparison_type**: yoy(同比)/mom(环比)/dod(日环比)/wow(周环比)
7. **filters**: 过滤条件，如{{"domain": "电商"}}

## 输出格式

请严格按照JSON格式输出：
```json
{{
    "core_query": "核心指标名",
    "time_range": null or {{"type": "...", "value": "...", "description": "..."}},
    "time_granularity": null or "day|week|month|quarter|year",
    "aggregation_type": null or "sum|avg|count|max|min|rate|ratio",
    "dimensions": [],
    "comparison_type": null or "yoy|mom|dod|wow",
    "filters": {{}},
    "confidence": 0.95,
    "reasoning": "详细的推理过程"
}}
```
{candidates_info}
## Few-Shot示例
{examples_text}
## 待识别查询

查询: {query}

请分析上述查询并输出JSON格式的意图信息（只输出JSON，不要输出其他内容）：
"""
        return prompt

    def generate_response(self, prompt: str, system_prompt: str = "你是一个专业的助手。") -> Optional[str]:
        """调用智谱API生成响应.

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词

        Returns:
            生成的文本内容，如果失败返回None
        """
        if not self.api_key:
            print("❌ 智谱API密钥未配置")
            return None

        try:
            # 构建JWT token
            token = self._generate_token()

            # 调用智谱API
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": system_prompt
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.1,
                        "top_p": 0.7,
                        "max_tokens": 1000,
                    }
                )

                response.raise_for_status()
                data = response.json()

            # 解析结果
            content = data["choices"][0]["message"]["content"]
            return content

        except Exception as e:
            print(f"❌ 智谱API调用失败: {e}")
            return None

    def recognize(self, query: str, candidates: list = None) -> Optional[ZhipuIntentResult]:
        """识别查询意图.

        Args:
            query: 用户查询文本
            candidates: 候选指标列表（从向量检索获取）

        Returns:
            智谱意图识别结果
        """
        start_time = time.time()

        try:
            # 构建Prompt
            prompt = self._build_prompt(query, candidates)
            
            # 调用LLM
            content = self.generate_response(
                prompt, 
                system_prompt="你是一个专业的BI查询意图识别专家。严格按照JSON格式输出结果，不要输出任何额外内容。"
            )
            
            if not content:
                return None

            # 清理可能的markdown标记
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            intent_data = json.loads(content)

            # 构建结果
            return ZhipuIntentResult(
                core_query=intent_data.get("core_query", query),
                time_range=intent_data.get("time_range"),
                time_granularity=intent_data.get("time_granularity"),
                aggregation_type=intent_data.get("aggregation_type"),
                dimensions=intent_data.get("dimensions", []),
                comparison_type=intent_data.get("comparison_type"),
                filters=intent_data.get("filters", {}),
                confidence=intent_data.get("confidence", 0.8),
                reasoning=intent_data.get("reasoning", ""),
                model=self.model,
                latency=time.time() - start_time,
                tokens_used={"total_tokens": 0} # 简化，如果需要精确统计需重构返回值
            )

        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            print(f"   原始响应: {content if 'content' in locals() else 'N/A'}")
            return None
        except Exception as e:
            print(f"❌ 智谱意图识别异常: {e}")
            return None

    def _generate_token(self) -> str:
        """生成智谱API的JWT token."""
        import hmac
        import hashlib
        import base64
        import time

        try:
            # 分离API密钥
            if "." not in self.api_key:
                raise ValueError("API Key格式错误，应为 id.secret")

            api_id, api_secret = self.api_key.split(".", 1)

            # 构造JWT payload
            now = int(time.time())
            payload = {
                "api_key": api_id,
                "exp": now + 3600,  # 1小时过期
                "timestamp": now
            }

            # 编码header和payload
            header = {"alg": "HS256", "sign_type": "SIGN"}

            header_b64 = base64.urlsafe_b64encode(
                json.dumps(header, separators=(',', ':')).encode()
            ).decode().rstrip('=')

            payload_b64 = base64.urlsafe_b64encode(
                json.dumps(payload, separators=(',', ':')).encode()
            ).decode().rstrip('=')

            # 生成签名
            message = f"{header_b64}.{payload_b64}"
            signature = hmac.new(
                api_secret.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()

            signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')

            # 组合JWT
            token = f"{header_b64}.{payload_b64}.{signature_b64}"
            return token

        except Exception as e:
            print(f"❌ Token生成失败: {e}")
            raise


# 测试函数
def test_zhipu_recognizer():
    """测试智谱意图识别器."""
    print("\n🧪 测试智谱AI意图识别")
    print("=" * 50)

    recognizer = ZhipuIntentRecognizer(model="glm-4-flash")

    test_queries = [
        "GMV是什么",
        "最近7天的成交金额",
        "本月营收总和",
        "按地区的DAU同比"
    ]

    for query in test_queries:
        print(f"\n查询: {query}")
        print("-" * 50)

        result = recognizer.recognize(query)

        if result:
            print(f"✅ 识别成功")
            print(f"   核心查询: {result.core_query}")
            print(f"   置信度: {result.confidence}")
            print(f"   耗时: {result.latency*1000:.2f}ms")
            print(f"   Tokens: {result.tokens_used['total_tokens']}")
            print(f"   推理: {result.reasoning}")
        else:
            print(f"❌ 识别失败")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    test_zhipu_recognizer()
