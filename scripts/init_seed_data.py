#!/usr/bin/env python3
"""示例数据初始化脚本.

创建 10 个示例指标并向量化后存储到 Qdrant.
"""

import sys
from pathlib import Path

import numpy as np
from tqdm import tqdm

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.recall.vector.models import MetricMetadata, VectorizedMetric
from src.recall.vector.qdrant_store import QdrantVectorStore
from src.recall.vector.vectorizer import MetricVectorizer


# 示例指标数据
SAMPLE_METRICS = [
    {
        "metric_id": "m001",
        "name": "GMV",
        "code": "gmv",
        "description": "一定时期内成交总额，反映平台整体交易规模",
        "synonyms": ["成交金额", "交易额", "总交易额", "成交总额"],
        "domain": "电商",
        "formula": "SUM(order_amount)",
    },
    {
        "metric_id": "m002",
        "name": "DAU",
        "code": "dau",
        "description": "日活跃用户数，统计一天内至少访问一次的用户数量",
        "synonyms": ["日活", "日活跃用户", "每日活跃用户"],
        "domain": "用户",
        "formula": "COUNT(DISTINCT user_id) WHERE date = TODAY",
    },
    {
        "metric_id": "m003",
        "name": "MAU",
        "code": "mau",
        "description": "月活跃用户数，统计一个月内至少访问一次的用户数量",
        "synonyms": ["月活", "月活跃用户", "每月活跃用户"],
        "domain": "用户",
        "formula": "COUNT(DISTINCT user_id) WHERE date >= TODAY - 30 DAYS",
    },
    {
        "metric_id": "m004",
        "name": "ARPU",
        "code": "arpu",
        "description": "每用户平均收入，衡量单用户价值",
        "synonyms": ["人均收入", "每用户收入"],
        "domain": "营收",
        "formula": "total_revenue / active_users",
    },
    {
        "metric_id": "m005",
        "name": "转化率",
        "code": "conversion_rate",
        "description": "访客转化为付费用户的比例",
        "synonyms": ["付费转化率", "转化率"],
        "domain": "增长",
        "formula": "paid_users / total_visitors * 100%",
    },
    {
        "metric_id": "m006",
        "name": "留存率",
        "code": "retention_rate",
        "description": "用户在特定时间段后继续使用产品的比例",
        "synonyms": ["用户留存", "留存比例"],
        "domain": "用户",
        "formula": "returning_users / initial_users * 100%",
    },
    {
        "metric_id": "m007",
        "name": "客单价",
        "code": "avg_order_value",
        "description": "平均每个订单的金额",
        "synonyms": ["平均订单金额", "AOV", "笔单价"],
        "domain": "电商",
        "formula": "SUM(order_amount) / COUNT(order_id)",
    },
    {
        "metric_id": "m008",
        "name": "复购率",
        "code": "repurchase_rate",
        "description": "用户在一段时间内重复购买的比例",
        "synonyms": ["重复购买率", "二次购买率"],
        "domain": "电商",
        "formula": "repeat_customers / total_customers * 100%",
    },
    {
        "metric_id": "m009",
        "name": "LTV",
        "code": "ltv",
        "description": "用户生命周期价值，单个用户在整个生命周期内贡献的总收入",
        "synonyms": ["生命周期价值", "客户终身价值", "CLV"],
        "domain": "营收",
        "formula": "ARPU * avg_lifespan",
    },
    {
        "metric_id": "m010",
        "name": "CAC",
        "code": "cac",
        "description": "获客成本，获取一个新用户所需的营销费用",
        "synonyms": ["获客成本", "用户获取成本"],
        "domain": "增长",
        "formula": "total_marketing_cost / new_customers",
    },
]


def main() -> None:
    """主函数."""
    print("=" * 60)
    print("示例数据初始化脚本")
    print("=" * 60)

    # 1. 初始化向量化器
    print("\n[1/4] 初始化向量化器...")
    vectorizer = MetricVectorizer(model_name=settings.vectorizer.model_name)
    print(f"✓ 模型加载成功: {settings.vectorizer.model_name}")
    print(f"  向量维度: {vectorizer.embedding_dim}")

    # 2. 创建 MetricMetadata 对象
    print("\n[2/4] 解析指标元数据...")
    metrics_metadata = []
    for metric_data in SAMPLE_METRICS:
        metadata = MetricMetadata(**metric_data)
        metrics_metadata.append(metadata)
    print(f"✓ 成功创建 {len(metrics_metadata)} 个指标元数据")

    # 3. 向量化
    print("\n[3/4] 批量向量化...")
    embeddings = vectorizer.vectorize_batch(metrics_metadata, show_progress=True)
    print(f"✓ 向量化完成，shape: {embeddings.shape}")

    # 4. 存储到 Qdrant
    print("\n[4/4] 存储到 Qdrant...")
    store = QdrantVectorStore(config=settings.qdrant)

    # 创建 collection（如果不存在）
    if not store.collection_exists():
        print(f"  创建 Collection: {settings.qdrant.collection_name}")
        store.create_collection(vector_size=vectorizer.embedding_dim, recreate=False)
    else:
        print(f"  Collection 已存在: {settings.qdrant.collection_name}")

    # 准备数据
    metric_ids = [m.metric_id for m in SAMPLE_METRICS]
    payloads = [
        {
            "metric_id": m.metric_id,
            "name": m["name"],
            "code": m["code"],
            "description": m["description"],
            "synonyms": m["synonyms"],
            "domain": m["domain"],
            "formula": m.get("formula"),
        }
        for m in SAMPLE_METRICS
    ]

    # 批量 upsert
    count = store.upsert(metric_ids, embeddings, payloads, batch_size=32)
    print(f"✓ 成功插入 {count} 条数据")

    # 验证
    total_count = store.count()
    print(f"\n当前 Collection 总数: {total_count}")

    # 测试检索
    print("\n测试检索功能...")
    query_text = "成交总额"
    query_metric = MetricMetadata(
        name=query_text,
        code="test",
        description="测试查询",
        synonyms=[],
        domain="测试",
    )
    query_vector = vectorizer.vectorize(query_metric)
    results = store.search(query_vector, top_k=3)

    print(f"\n查询: '{query_text}' 的 Top-3 结果:")
    for i, result in enumerate(results, 1):
        payload = result["payload"]
        print(f"  {i}. {payload['name']} ({payload['code']}) - 相似度: {result['score']:.4f}")

    print("\n" + "=" * 60)
    print("✓ 初始化完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
