#!/usr/bin/env python3
"""初始化 Neo4j 图谱数据."""

import os
import sys

from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.recall.graph.graph_store import GraphStore
from src.recall.graph.importer import GraphImporter, SAMPLE_DOMAINS, SAMPLE_METRICS, SAMPLE_RELATIONS
from src.recall.graph.neo4j_client import Neo4jClient


def main() -> None:
    """主函数."""
    print("=" * 60)
    print("🔮 Neo4j 图谱数据初始化")
    print("=" * 60)

    # 读取环境变量
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD", "password")

    print(f"\n连接配置:")
    print(f"  URI: {neo4j_uri}")
    print(f"  用户: {neo4j_user}")

    # 1. 连接 Neo4j
    print("\n[1/5] 连接 Neo4j...")
    client = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
    try:
        client.connect()
        print("  ✓ 连接成功")
    except Exception as e:
        print(f"  ✗ 连接失败: {e}")
        print("\n提示:")
        print("  1. 确保 Neo4j 正在运行: docker run -p 7687:7687 neo4j")
        print("  2. 检查环境变量: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")
        return

    # 2. 初始化图谱结构
    print("\n[2/5] 初始化图谱结构...")
    graph_store = GraphStore(client)
    graph_store.init_schema()
    print("  ✓ 约束和索引已创建")

    # 3. 导入业务域
    print("\n[3/5] 导入业务域...")
    importer = GraphImporter(graph_store)
    count = importer.import_domains_batch(SAMPLE_DOMAINS)
    print(f"  ✓ 导入 {count} 个业务域")

    # 4. 导入指标
    print("\n[4/5] 导入指标...")
    count = importer.import_metrics_batch(SAMPLE_METRICS)
    print(f"  ✓ 导入 {count} 个指标")

    # 5. 导入关系
    print("\n[5/5] 导入关系...")
    count = importer.import_relations_batch(SAMPLE_RELATIONS)
    print(f"  ✓ 导入 {count} 个关系")

    # 验证
    print("\n" + "=" * 60)
    print("📊 数据验证")
    print("=" * 60)

    # 统计节点数
    result = client.execute_query("MATCH (n) RETURN count(n) as count")
    total_nodes = result[0]["count"]
    print(f"\n总节点数: {total_nodes}")

    # 统计关系数
    result = client.execute_query("MATCH ()-[r]->() RETURN count(r) as count")
    total_rels = result[0]["count"]
    print(f"总关系数: {total_rels}")

    # 示例查询
    print("\n示例查询 - 查找 '用户' 域的指标:")
    metrics = graph_store.find_metrics_by_domain("用户")
    for metric in metrics[:3]:
        m = metric["m"]
        print(f"  - {m['name']} ({m['code']}): {m['description']}")

    print("\n示例查询 - 查找 DAU 的相关指标:")
    related = graph_store.find_related_metrics("m002", max_depth=2)
    for rel in related[:3]:
        print(f"  - {rel['name']} ({rel['code']})")

    print("\n" + "=" * 60)
    print("✓ 初始化完成！")
    print("=" * 60)

    # 关闭连接
    client.close()


if __name__ == "__main__":
    main()
