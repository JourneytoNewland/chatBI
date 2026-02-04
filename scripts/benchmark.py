#!/usr/bin/env python3
"""性能基准测试脚本.

测试向量检索系统的性能指标：
- 召回率
- P99 延迟
- QPS
- 向量化速度
"""

import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.recall.vector.models import MetricMetadata
from src.recall.vector.qdrant_store import QdrantVectorStore
from src.recall.vector.vectorizer import MetricVectorizer


# 测试数据
TEST_METRICS = [
    {
        "name": "GMV",
        "code": "gmv",
        "description": "成交总额",
        "synonyms": ["成交金额", "交易额"],
        "domain": "电商",
    },
    {
        "name": "DAU",
        "code": "dau",
        "description": "日活跃用户数",
        "synonyms": ["日活"],
        "domain": "用户",
    },
    {
        "name": "MAU",
        "code": "mau",
        "description": "月活跃用户数",
        "synonyms": ["月活"],
        "domain": "用户",
    },
    {
        "name": "ARPU",
        "code": "arpu",
        "description": "每用户平均收入",
        "synonyms": ["人均收入"],
        "domain": "营收",
    },
    {
        "name": "转化率",
        "code": "conversion_rate",
        "description": "访客转化为付费用户的比例",
        "synonyms": ["付费转化率"],
        "domain": "增长",
    },
]


def benchmark_vectorization(vectorizer: MetricVectorizer, n_warmup: int = 3) -> dict[str, Any]:
    """测试向量化性能.

    Args:
        vectorizer: 向量化器实例
        n_warmup: 预热次数

    Returns:
        性能指标字典
    """
    print("\n" + "=" * 60)
    print("📊 向量化性能测试")
    print("=" * 60)

    metrics = [MetricMetadata(**m) for m in TEST_METRICS]

    # 预热
    print(f"\n预热 {n_warmup} 次...")
    for _ in range(n_warmup):
        _ = vectorizer.vectorize_batch(metrics, show_progress=False)

    # 测试单条向量化
    print("\n测试单条向量化...")
    latencies = []
    for _ in range(10):
        start = time.time()
        _ = vectorizer.vectorize(metrics[0])
        latencies.append((time.time() - start) * 1000)

    single_avg = np.mean(latencies)
    single_p99 = np.percentile(latencies, 99)
    print(f"  平均延迟: {single_avg:.2f} ms")
    print(f"  P99 延迟: {single_p99:.2f} ms")

    # 测试批量向量化
    print("\n测试批量向量化...")
    latencies = []
    for _ in range(10):
        start = time.time()
        _ = vectorizer.vectorize_batch(metrics, show_progress=False)
        latencies.append((time.time() - start) * 1000)

    batch_avg = np.mean(latencies)
    batch_p99 = np.percentile(latencies, 99)
    print(f"  平均延迟: {batch_avg:.2f} ms")
    print(f"  P99 延迟: {batch_p99:.2f} ms")
    print(f"  平均每条: {batch_avg / len(metrics):.2f} ms")

    return {
        "single_avg_ms": single_avg,
        "single_p99_ms": single_p99,
        "batch_avg_ms": batch_avg,
        "batch_p99_ms": batch_p99,
        "batch_per_item_ms": batch_avg / len(metrics),
    }


def benchmark_search(
    vectorizer: MetricVectorizer,
    vector_store: QdrantVectorStore,
    n_queries: int = 100,
) -> dict[str, Any]:
    """测试检索性能.

    Args:
        vectorizer: 向量化器实例
        vector_store: 向量存储实例
        n_queries: 查询次数

    Returns:
        性能指标字典
    """
    print("\n" + "=" * 60)
    print("🔍 检索性能测试")
    print("=" * 60)

    # 准备查询
    query = "成交总额"
    query_metadata = MetricMetadata(
        name=query,
        code=query,
        description=query,
        synonyms=[],
        domain="查询",
    )
    query_vector = vectorizer.vectorize(query_metadata)

    # 预热
    print(f"\n预热 10 次...")
    for _ in range(10):
        _ = vector_store.search(query_vector, top_k=10)

    # 测试检索延迟
    print(f"\n执行 {n_queries} 次查询...")
    latencies = []
    for _ in range(n_queries):
        start = time.time()
        _ = vector_store.search(query_vector, top_k=10)
        latencies.append((time.time() - start) * 1000)

    avg_latency = np.mean(latencies)
    p50_latency = np.percentile(latencies, 50)
    p95_latency = np.percentile(latencies, 95)
    p99_latency = np.percentile(latencies, 99)
    min_latency = np.min(latencies)
    max_latency = np.max(latencies)

    print(f"\n延迟统计:")
    print(f"  平均: {avg_latency:.2f} ms")
    print(f"  P50: {p50_latency:.2f} ms")
    print(f"  P95: {p95_latency:.2f} ms")
    print(f"  P99: {p99_latency:.2f} ms")
    print(f"  最小: {min_latency:.2f} ms")
    print(f"  最大: {max_latency:.2f} ms")

    # 计算 QPS
    qps = 1000 / avg_latency
    print(f"\nQPS: {qps:.2f}")

    return {
        "avg_ms": avg_latency,
        "p50_ms": p50_latency,
        "p95_ms": p95_latency,
        "p99_ms": p99_latency,
        "min_ms": min_latency,
        "max_ms": max_latency,
        "qps": qps,
    }


def benchmark_recall(
    vectorizer: MetricVectorizer,
    vector_store: QdrantVectorStore,
) -> dict[str, Any]:
    """测试召回率.

    Args:
        vectorizer: 向量化器实例
        vector_store: 向量存储实例

    Returns:
        召回率指标
    """
    print("\n" + "=" * 60)
    print("🎯 召回率测试")
    print("=" * 60)

    # 测试查询
    test_cases = [
        {
            "query": "GMV",
            "expected": "GMV",
            "description": "精确匹配",
        },
        {
            "query": "成交总额",
            "expected": "GMV",
            "description": "同义词查询",
        },
        {
            "query": "日活用户",
            "expected": "DAU",
            "description": "同义变体",
        },
    ]

    recall_results = []

    for case in test_cases:
        query = case["query"]
        expected = case["expected"]
        description = case["description"]

        # 向量化查询
        query_metadata = MetricMetadata(
            name=query,
            code=query,
            description=query,
            synonyms=[],
            domain="查询",
        )
        query_vector = vectorizer.vectorize(query_metadata)

        # 检索
        results = vector_store.search(query_vector, top_k=5)

        # 检查预期结果是否在 Top-K 中
        found = any(r["payload"]["name"] == expected for r in results)
        rank = next((i + 1 for i, r in enumerate(results) if r["payload"]["name"] == expected), None)

        print(f"\n{description}: '{query}' -> '{expected}'")
        print(f"  找到: {'✓' if found else '✗'}")
        if found and rank:
            print(f"  排名: {rank}")

        recall_results.append(
            {
                "query": query,
                "expected": expected,
                "found": found,
                "rank": rank,
                "description": description,
            }
        )

    # 计算召回率
    recall_rate = sum(1 for r in recall_results if r["found"]) / len(recall_results)
    print(f"\n总体召回率: {recall_rate * 100:.1f}%")

    return {
        "recall_rate": recall_rate,
        "details": recall_results,
    }


def main() -> None:
    """主函数."""
    print("=" * 60)
    print("🚀 性能基准测试")
    print("=" * 60)

    # 1. 初始化
    print("\n[1/4] 初始化组件...")
    vectorizer = MetricVectorizer(model_name=settings.vectorizer.model_name)
    print(f"  ✓ 向量化器: {settings.vectorizer.model_name}")

    # 使用内存模式 Qdrant
    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name="benchmark",
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )

    config = settings.qdrant
    config.collection_name = "benchmark"
    vector_store = QdrantVectorStore(config=config)
    vector_store.client = client
    print(f"  ✓ 向量存储: {config.collection_name}")

    # 2. 准备测试数据
    print("\n[2/4] 准备测试数据...")
    metrics = [MetricMetadata(**m) for m in TEST_METRICS]
    embeddings = vectorizer.vectorize_batch(metrics, show_progress=False)

    metric_ids = [f"m{i:03d}" for i in range(len(metrics))]
    payloads = [
        {
            "metric_id": mid,
            "name": m.name,
            "code": m.code,
            "description": m.description,
            "synonyms": m.synonyms,
            "domain": m.domain,
        }
        for mid, m in zip(metric_ids, metrics)
    ]

    vector_store.upsert(metric_ids, embeddings, payloads)
    print(f"  ✓ 插入 {len(metrics)} 条测试数据")

    # 3. 运行性能测试
    vectorization_results = benchmark_vectorization(vectorizer)
    search_results = benchmark_search(vectorizer, vector_store)
    recall_results = benchmark_recall(vectorizer, vector_store)

    # 4. 汇总结果
    print("\n" + "=" * 60)
    print("📋 性能测试汇总")
    print("=" * 60)

    print("\n向量化性能:")
    print(f"  单条延迟: {vectorization_results['single_avg_ms']:.2f} ms (P99: {vectorization_results['single_p99_ms']:.2f} ms)")
    print(f"  批量延迟: {vectorization_results['batch_avg_ms']:.2f} ms (P99: {vectorization_results['batch_p99_ms']:.2f} ms)")

    print("\n检索性能:")
    print(f"  平均延迟: {search_results['avg_ms']:.2f} ms")
    print(f"  P95 延迟: {search_results['p95_ms']:.2f} ms")
    print(f"  P99 延迟: {search_results['p99_ms']:.2f} ms")
    print(f"  QPS: {search_results['qps']:.2f}")

    print("\n召回率:")
    print(f"  总体召回率: {recall_results['recall_rate'] * 100:.1f}%")

    # 验证目标
    print("\n" + "=" * 60)
    print("🎯 目标验证")
    print("=" * 60)

    target_p99 = 50.0  # ms
    target_recall = 0.85  # 85%

    p99_passed = search_results["p99_ms"] <= target_p99
    recall_passed = recall_results["recall_rate"] >= target_recall

    print(f"\nP99 延迟 ≤ {target_p99} ms: {'✓ 通过' if p99_passed else '✗ 未通过'} ({search_results['p99_ms']:.2f} ms)")
    print(f"召回率 ≥ {target_recall * 100}%: {'✓ 通过' if recall_passed else '✗ 未通过'} ({recall_results['recall_rate'] * 100:.1f}%)")

    all_passed = p99_passed and recall_passed
    print(f"\n总体结果: {'✓ 全部通过' if all_passed else '✗ 部分未通过'}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
