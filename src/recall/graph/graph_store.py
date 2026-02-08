
from typing import List, Dict, Any, Optional
from src.recall.graph.neo4j_client import Neo4jClient
from src.config.settings import settings

class GraphStore:
    """知识图谱存储服务 (业务层封装)."""

    def __init__(self):
        self.client = Neo4jClient(
            uri=settings.neo4j.uri,
            user=settings.neo4j.user,
            password=settings.neo4j.password
        )

    def close(self):
        self.client.close()

    def clear_data(self):
        """清空所有数据 (慎用)."""
        query = "MATCH (n) DETACH DELETE n"
        self.client.execute_write(query)

    def create_constraints(self):
        """创建索引和约束."""
        # 针对 Neo4j 5.x+ 语法可能不同，这里使用较通用的
        try:
            self.client.execute_write("CREATE CONSTRAINT IF NOT EXISTS FOR (m:Metric) REQUIRE m.id IS UNIQUE")
            self.client.execute_write("CREATE INDEX IF NOT EXISTS FOR (m:Metric) ON (m.name)")
            self.client.execute_write("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Domain) REQUIRE d.name IS UNIQUE")
        except Exception as e:
            print(f"⚠️ Failed to create constraints (might already exist or syntax diff): {e}")

    def upsert_metric(self, metric: Dict[str, Any]):
        """更新或插入指标节点及关系."""
        # 1. Merge Metric Node
        query_metric = """
        MERGE (m:Metric {id: $id})
        SET m.name = $name,
            m.code = $code,
            m.description = $description,
            m.formula = $formula,
            m.updated_at = datetime()
        """
        self.client.execute_write(query_metric, {
            "id": metric['id'],
            "name": metric['name'],
            "code": metric['code'],
            "description": metric.get('description', ''),
            "formula": metric.get('formula', '')
        })

        # 2. Link to Domain
        if metric.get('domain'):
            query_domain = """
            MERGE (d:Domain {name: $domain})
            WITH d
            MATCH (m:Metric {id: $id})
            MERGE (m)-[:BELONGS_TO]->(d)
            """
            self.client.execute_write(query_domain, {
                "domain": metric['domain'],
                "id": metric['id']
            })

    def search_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """根据领域查找指标."""
        query = """
        MATCH (m:Metric)-[:BELONGS_TO]->(d:Domain)
        WHERE d.name CONTAINS $domain
        RETURN m.id as id, m.name as name, m.description as description, d.name as domain
        """
        return self.client.execute_query(query, {"domain": domain})

    def get_related_metrics(self, metric_id: str) -> List[Dict[str, Any]]:
        """查找相关指标 (同一领域)."""
        query = """
        MATCH (m:Metric {id: $id})-[:BELONGS_TO]->(d:Domain)<-[:BELONGS_TO]-(other:Metric)
        RETURN other.id as id, other.name as name, d.name as domain
        LIMIT 10
        """
        return self.client.execute_query(query, {"id": metric_id})
