"""知识图谱增强的意图识别模块."""

from typing import Any, Optional
from dataclasses import dataclass

from neo4j import GraphDatabase

from .intent import QueryIntent, IntentRecognizer


@dataclass
class GraphEntity:
    """图谱实体."""
    entity_id: str
    name: str
    type: str  # Metric, Dimension, Domain, etc.
    properties: dict[str, Any]


@dataclass
class GraphRelation:
    """图谱关系."""
    source: str
    target: str
    relation_type: str
    properties: dict[str, Any]


class GraphEnhancedIntentRecognizer:
    """知识图谱增强的意图识别器.

    功能:
    1. 同义词扩展 - 利用SYNONYM关系扩展查询
    2. 领域约束 - 利用DOMAIN关系添加过滤条件
    3. 层次关系 - 利用BELONGS_TO关系识别上下级指标
    4. 计算规则 - 利用CALCULATED_BY关系提供计算公式
    5. 使用示例 - 利用EXAMPLE关系提供示例查询
    """

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "12345678"
    ):
        """初始化图谱增强识别器.

        Args:
            neo4j_uri: Neo4j连接URI
            neo4j_user: 用户名
            neo4j_password: 密码
        """
        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )

        # 基础识别器
        self.base_recognizer = IntentRecognizer()

        print("✅ 图谱增强识别器初始化完成")

    def recognize(self, query: str) -> QueryIntent:
        """使用图谱增强识别查询意图.

        Args:
            query: 用户查询文本

        Returns:
            增强的查询意图
        """
        # 1. 基础意图识别
        intent = self.base_recognizer.recognize(query)

        # 2. 从图谱中增强
        enhanced = self._enhance_with_graph(query, intent)

        return enhanced

    def _enhance_with_graph(self, query: str, intent: QueryIntent) -> QueryIntent:
        """使用图谱增强意图.

        Args:
            query: 原始查询
            intent: 基础识别的意图

        Returns:
            增强后的意图
        """
        core_query = intent.core_query

        # 1. 同义词扩展
        synonyms = self._get_synonyms(core_query)
        if synonyms and not intent.filters.get("synonyms"):
            intent.filters["synonyms"] = synonyms
            print(f"   📊 发现同义词: {synonyms}")

        # 2. 领域识别
        domain = self._infer_domain(core_query, query)
        if domain:
            intent.filters["domain"] = domain
            print(f"   🏷️  识别领域: {domain}")

        # 3. 相关指标推荐
        related_metrics = self._get_related_metrics(core_query)
        if related_metrics:
            intent.filters["related_metrics"] = related_metrics
            print(f"   🔗 相关指标: {related_metrics}")

        # 4. 计算公式
        formula = self._get_formula(core_query)
        if formula:
            intent.filters["formula"] = formula
            print(f"   🧮 计算公式: {formula}")

        # 5. 使用示例
        examples = self._get_examples(core_query)
        if examples:
            intent.filters["examples"] = examples
            print(f"   💡 使用示例: {examples[:2]}")

        return intent

    def _get_synonyms(self, entity_name: str) -> list[str]:
        """获取实体的同义词.

        Args:
            entity_name: 实体名称

        Returns:
            同义词列表
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (m:Metric {name: $name})-[:SYNONYM]->(syn)
                RETURN syn.name as synonym
                UNION
                MATCH (syn:Metric)-[:SYNONYM]->(m:Metric {name: $name})
                RETURN syn.name as synonym
                """,
                name=entity_name
            )
            return [record["synonym"] for record in result]

    def _infer_domain(self, core_query: str, full_query: str) -> Optional[str]:
        """推断业务领域.

        Args:
            core_query: 核心查询词
            full_query: 完整查询

        Returns:
            业务领域名称
        """
        with self.driver.session() as session:
            # 1. 直接匹配
            result = session.run(
                """
                MATCH (m:Metric {name: $name})-[:BELONGS_TO]->(d:Domain)
                RETURN d.name as domain
                """,
                name=core_query
            )

            for record in result:
                return record["domain"]

            # 2. 通过同义词推断
            result = session.run(
                """
                MATCH (syn:Metric)-[:SYNONYM]->(m:Metric {name: $name})
                MATCH (m)-[:BELONGS_TO]->(d:Domain)
                RETURN d.name as domain
                """,
                name=core_query
            )

            for record in result:
                return record["domain"]

        return None

    def _get_related_metrics(self, entity_name: str) -> list[str]:
        """获取相关指标.

        Args:
            entity_name: 实体名称

        Returns:
            相关指标列表
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (m:Metric {name: $name})-[:RELATED_TO]-(related:Metric)
                RETURN DISTINCT related.name as metric
                LIMIT 5
                """,
                name=entity_name
            )
            return [record["metric"] for record in result]

    def _get_formula(self, entity_name: str) -> Optional[str]:
        """获取计算公式.

        Args:
            entity_name: 实体名称

        Returns:
            计算公式字符串
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (m:Metric {name: $name})-[:CALCULATED_BY]->(f:Formula)
                RETURN f.expression as formula
                """,
                name=entity_name
            )

            for record in result:
                return record["formula"]

        return None

    def _get_examples(self, entity_name: str) -> list[str]:
        """获取使用示例.

        Args:
            entity_name: 实体名称

        Returns:
            示例查询列表
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (m:Metric {name: $name})-[:EXAMPLE]->(q:Query)
                RETURN q.text as example
                LIMIT 3
                """,
                name=entity_name
            )
            return [record["example"] for record in result]

    def get_graph_statistics(self) -> dict[str, Any]:
        """获取图谱统计信息.

        Returns:
            统计数据字典
        """
        with self.driver.session() as session:
            # 节点统计
            metrics_count = session.run(
                "MATCH (m:Metric) RETURN count(m) as count"
            ).single()["count"]

            domains_count = session.run(
                "MATCH (d:Domain) RETURN count(d) as count"
            ).single()["count"]

            # 关系统计
            synonym_relations = session.run(
                "MATCH ()-[r:SYNONYM]->() RETURN count(r) as count"
            ).single()["count"]

            belongs_to_relations = session.run(
                "MATCH ()-[r:BELONGS_TO]->() RETURN count(r) as count"
            ).single()["count"]

            related_to_relations = session.run(
                "MATCH ()-[r:RELATED_TO]->() RETURN count(r) as count"
            ).single()["count"]

            return {
                "nodes": {
                    "metrics": metrics_count,
                    "domains": domains_count,
                    "total": metrics_count + domains_count
                },
                "relations": {
                    "synonym": synonym_relations,
                    "belongs_to": belongs_to_relations,
                    "related_to": related_to_relations,
                    "total": synonym_relations + belongs_to_relations + related_to_relations
                }
            }

    def suggest_improvements(self, query: str, intent: QueryIntent) -> list[dict[str, Any]]:
        """基于图谱提供语义优化建议.

        Args:
            query: 用户查询
            intent: 识别的意图

        Returns:
            建议列表
        """
        suggestions = []

        with self.driver.session() as session:
            # 1. 检查是否有未链接的同义词
            core_query = intent.core_query

            # 查找相似但未链接的指标
            result = session.run(
                """
                MATCH (m:Metric)
                WHERE m.name <> $name
                  AND (m.name CONTAINS $name OR $name CONTAINS m.name)
                  AND NOT EXISTS((m)-[:SYNONYM]-(:Metric {name: $name}))
                RETURN m.name as similar_metric
                LIMIT 3
                """,
                name=core_query
            )

            for record in result:
                suggestions.append({
                    "type": "synonym_link",
                    "priority": "medium",
                    "message": f"建议将 '{record['similar_metric']}' 与 '{core_query}' 建立同义词关系",
                    "action": "CREATE_SYNONYM_LINK",
                    "entities": [core_query, record["similar_metric"]]
                })

            # 2. 检查是否缺少领域标注
            domain = self._infer_domain(core_query, query)
            if not domain:
                suggestions.append({
                    "type": "domain_annotation",
                    "priority": "high",
                    "message": f"指标 '{core_query}' 缺少业务领域标注",
                    "action": "ADD_DOMAIN",
                    "entities": [core_query]
                })

            # 3. 检查是否缺少计算公式
            formula = self._get_formula(core_query)
            if not formula:
                suggestions.append({
                    "type": "formula_annotation",
                    "priority": "low",
                    "message": f"建议为指标 '{core_query}' 添加计算公式",
                    "action": "ADD_FORMULA",
                    "entities": [core_query]
                })

            # 4. 检查是否缺少使用示例
            examples = self._get_examples(core_query)
            if len(examples) < 3:
                suggestions.append({
                    "type": "example_enrichment",
                    "priority": "medium",
                    "message": f"建议为指标 '{core_query}' 添加更多使用示例（当前{len(examples)}个）",
                    "action": "ADD_EXAMPLES",
                    "entities": [core_query]
                })

        return suggestions

    def search_graph(self, pattern: str, limit: int = 10) -> list[dict[str, Any]]:
        """在图谱中搜索匹配的实体和关系.

        Args:
            pattern: 搜索模式
            limit: 返回数量限制

        Returns:
            匹配结果列表
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (m:Metric)
                WHERE m.name CONTAINS $pattern
                   OR m.description CONTAINS $pattern
                OPTIONAL MATCH (m)-[r:SYNONYM|RELATED_TO|BELONGS_TO]-(other)
                RETURN m.name as name,
                       m.description as description,
                       type(r) as relation_type,
                       other.name as related_name
                LIMIT $limit
                """,
                pattern=pattern,
                limit=limit
            )

            return [
                {
                    "name": record["name"],
                    "description": record["description"],
                    "relation_type": record["relation_type"],
                    "related_name": record["related_name"]
                }
                for record in result
            ]

    def close(self):
        """关闭数据库连接."""
        self.driver.close()


# 测试函数
def test_graph_enhanced_recognizer():
    """测试图谱增强识别器."""
    print("\n🧪 测试图谱增强意图识别")
    print("=" * 60)

    recognizer = GraphEnhancedIntentRecognizer()

    # 获取图谱统计
    stats = recognizer.get_graph_statistics()
    print("\n📊 图谱统计:")
    print(f"   节点: {stats['nodes']['total']} 个")
    print(f"     - 指标: {stats['nodes']['metrics']} 个")
    print(f"     - 领域: {stats['nodes']['domains']} 个")
    print(f"   关系: {stats['relations']['total']} 条")
    print(f"     - 同义词: {stats['relations']['synonym']} 条")
    print(f"     - 领域: {stats['relations']['belongs_to']} 条")
    print(f"     - 相关: {stats['relations']['related_to']} 条")

    # 测试增强识别
    test_query = "最近7天的GMV"
    print(f"\n查询: {test_query}")
    print("-" * 60)

    intent = recognizer.recognize(test_query)

    print(f"\n✅ 增强识别结果:")
    print(f"   核心查询: {intent.core_query}")
    print(f"   时间范围: {intent.time_range}")
    print(f"   过滤条件: {intent.filters}")

    # 获取优化建议
    print(f"\n💡 语义优化建议:")
    suggestions = recognizer.suggest_improvements(test_query, intent)

    for i, suggestion in enumerate(suggestions, 1):
        print(f"   {i}. [{suggestion['priority'].upper()}] {suggestion['message']}")
        print(f"      操作: {suggestion['action']}")

    recognizer.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_graph_enhanced_recognizer()
