#!/usr/bin/env python3
"""
诊断向量检索问题
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.recall.vector.qdrant_store import QdrantVectorStore
from src.recall.vector.vectorizer import MetricVectorizer

# 测试查询
test_queries = [
    "销售额",
    "订单数量",
    "用户留存",
    "投资回报"
]

vectorizer = MetricVectorizer()
vector_store = QdrantVectorStore()

print("="*80)
print("向量检索诊断")
print("="*80)

for query in test_queries:
    print(f"\n查询: '{query}'")
    query_vec = vectorizer.model.encode(query, normalize_embeddings=True)
    results = vector_store.search(query_vec, top_k=5, score_threshold=0.0)
    
    print(f"  Top 5 结果:")
    for i, result in enumerate(results[:5], 1):
        print(f"    {i}. {result['payload']['name']} (score={result['score']:.4f})")
        if i == 1:
            print(f"       同义词: {result['payload'].get('synonyms', [])}")
