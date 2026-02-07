"""图谱管理API端点."""

from typing import Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/graph", tags=["graph-management"])


# 模拟图谱数据
MOCK_GRAPH_NODES = [
    {
        "id": "gmv",
        "name": "GMV",
        "type": "Metric",
        "description": "成交总额（Gross Merchandise Volume）",
        "domain": "电商",
        "code": "gmv",
        "synonyms": ["成交金额", "交易额", "成交总额", "销售额"],
        "formula": "SUM(order_amount)"
    },
    {
        "id": "dau",
        "name": "DAU",
        "type": "Metric",
        "description": "日活跃用户数（Daily Active Users）",
        "domain": "用户",
        "code": "dau",
        "synonyms": ["日活", "日活跃用户", "每日活跃用户"],
        "formula": "COUNT(active_users WHERE date = current_date)"
    },
    {
        "id": "mau",
        "name": "MAU",
        "type": "Metric",
        "description": "月活跃用户数（Monthly Active Users）",
        "domain": "用户",
        "code": "mau",
        "synonyms": ["月活", "月活跃用户", "每月活跃用户"],
        "formula": "COUNT(active_users WHERE month = current_month)"
    },
    {
        "id": "arpu",
        "name": "ARPU",
        "type": "Metric",
        "description": "平均每用户收入（Average Revenue Per User）",
        "domain": "营收",
        "code": "arpu",
        "synonyms": ["人均收入", "每用户平均收入"],
        "formula": "SUM(revenue) / COUNT(users)"
    },
    {
        "id": "conversion_rate",
        "name": "转化率",
        "type": "Metric",
        "description": "访客转化为用户的比例",
        "domain": "营销",
        "code": "conversion_rate",
        "synonyms": ["转化比率", "访问转化率"],
        "formula": "COUNT(conversions) / COUNT(visitors)"
    },
    {
        "id": "ecommerce",
        "name": "电商",
        "type": "Domain",
        "description": "电商业务域"
    },
    {
        "id": "user",
        "name": "用户",
        "type": "Domain",
        "description": "用户业务域"
    },
    {
        "id": "revenue",
        "name": "营收",
        "type": "Domain",
        "description": "营收业务域"
    },
]

MOCK_GRAPH_RELATIONS = [
    {"source": "gmv", "target": "ecommerce", "type": "BELONGS_TO"},
    {"source": "dau", "target": "user", "type": "BELONGS_TO"},
    {"source": "mau", "target": "user", "type": "BELONGS_TO"},
    {"source": "arpu", "target": "revenue", "type": "BELONGS_TO"},
    {"source": "conversion_rate", "target": "ecommerce", "type": "BELONGS_TO"},
    {"source": "dau", "target": "mau", "type": "RELATED_TO"},
    {"source": "gmv", "target": "arpu", "type": "RELATED_TO"},
    {"source": "gmv", "target": "成交金额", "type": "SYNONYM"},
    {"source": "dau", "target": "日活", "type": "SYNONYM"},
    {"source": "mau", "target": "月活", "type": "SYNONYM"},
]


class GraphStatistics(BaseModel):
    """图谱统计信息."""
    nodes: dict[str, int]
    relations: dict[str, int]


class GraphNode(BaseModel):
    """图谱节点."""
    id: str
    name: str
    type: str
    description: str
    domain: str = None
    code: str = None
    synonyms: List[str] = []
    formula: str = None


class GraphRelation(BaseModel):
    """图谱关系."""
    source: str
    target: str
    type: str


class SuggestionItem(BaseModel):
    """优化建议项."""
    priority: str  # high/medium/low
    type: str
    message: str
    action: str
    entities: List[str]


class EditRequest(BaseModel):
    """编辑请求."""
    action: str  # ADD_NODE, ADD_RELATION, DELETE_NODE, DELETE_RELATION
    entity_type: str  # node, relation
    data: dict[str, Any]


@router.get("/statistics", response_model=GraphStatistics)
async def get_graph_statistics():
    """获取图谱统计信息."""
    nodes_total = len(MOCK_GRAPH_NODES)
    metrics_count = len([n for n in MOCK_GRAPH_NODES if n["type"] == "Metric"])
    domains_count = len([n for n in MOCK_GRAPH_NODES if n["type"] == "Domain"])

    relations_total = len(MOCK_GRAPH_RELATIONS)
    synonym_count = len([r for r in MOCK_GRAPH_RELATIONS if r["type"] == "SYNONYM"])
    belongs_count = len([r for r in MOCK_GRAPH_RELATIONS if r["type"] == "BELONGS_TO"])
    related_count = len([r for r in MOCK_GRAPH_RELATIONS if r["type"] == "RELATED_TO"])

    return GraphStatistics(
        nodes={
            "total": nodes_total,
            "metrics": metrics_count,
            "domains": domains_count
        },
        relations={
            "total": relations_total,
            "synonym": synonym_count,
            "belongs_to": belongs_count,
            "related_to": related_count
        }
    )


@router.get("/nodes", response_model=List[GraphNode])
async def list_nodes(node_type: str = None):
    """获取所有节点."""
    nodes = MOCK_GRAPH_NODES

    if node_type:
        nodes = [n for n in nodes if n["type"] == node_type]

    return [GraphNode(**n) for n in nodes]


@router.get("/relations", response_model=List[GraphRelation])
async def list_relations(relation_type: str = None):
    """获取所有关系."""
    relations = MOCK_GRAPH_RELATIONS

    if relation_type:
        relations = [r for r in relations if r["type"] == relation_type]

    return [GraphRelation(**r) for r in relations]


@router.get("/search")
async def search_graph(q: str, limit: int = 10):
    """搜索图谱中的节点和关系."""
    query = q.lower()

    # 搜索节点
    matched_nodes = [
        node for node in MOCK_GRAPH_NODES
        if query in node["name"].lower() or
           query in node["description"].lower() or
           any(query in syn.lower() for syn in node.get("synonyms", []))
    ]

    # 搜索关系
    matched_relations = [
        rel for rel in MOCK_GRAPH_RELATIONS
        if query in rel["source"].lower() or query in rel["target"].lower()
    ]

    return {
        "nodes": matched_nodes[:limit],
        "relations": matched_relations[:limit],
        "total": len(matched_nodes) + len(matched_relations)
    }


@router.get("/suggestions", response_model=List[SuggestionItem])
async def get_suggestions(query: str = None):
    """获取语义优化建议."""
    suggestions = [
        {
            "priority": "high",
            "type": "domain_annotation",
            "message": "指标 'GMV' 缺少详细的业务领域标注",
            "action": "ADD_DOMAIN",
            "entities": ["GMV"]
        },
        {
            "priority": "medium",
            "type": "synonym_link",
            "message": "建议将 '成交金额' 与 'GMV' 建立同义词关系",
            "action": "CREATE_SYNONYM_LINK",
            "entities": ["GMV", "成交金额"]
        },
        {
            "priority": "medium",
            "type": "formula_annotation",
            "message": "建议为指标 'DAU' 添加计算公式",
            "action": "ADD_FORMULA",
            "entities": ["DAU"]
        },
        {
            "priority": "low",
            "type": "example_enrichment",
            "message": "建议为指标 'MAU' 添加更多使用示例（当前1个）",
            "action": "ADD_EXAMPLES",
            "entities": ["MAU"]
        },
    ]

    # 如果指定了查询，过滤相关建议
    if query:
        suggestions = [
            s for s in suggestions
            if any(entity.lower() in query.lower() for entity in s["entities"])
        ]

    return [SuggestionItem(**s) for s in suggestions]


@router.post("/edit")
async def edit_graph(request: EditRequest):
    """编辑图谱（添加/删除节点或关系）."""
    action = request.action
    entity_type = request.entity_type
    data = request.data

    # 模拟编辑操作
    if action == "ADD_NODE" and entity_type == "node":
        new_node = {
            "id": data.get("id", f"node_{len(MOCK_GRAPH_NODES)}"),
            "name": data["name"],
            "type": data.get("type", "Metric"),
            "description": data.get("description", ""),
            "domain": data.get("domain"),
            "code": data.get("code"),
            "synonyms": data.get("synonyms", []),
            "formula": data.get("formula")
        }
        MOCK_GRAPH_NODES.append(new_node)

        return {
            "success": True,
            "message": f"节点 '{new_node['name']}' 已添加",
            "entity": new_node
        }

    elif action == "ADD_RELATION" and entity_type == "relation":
        new_relation = {
            "source": data["source"],
            "target": data["target"],
            "type": data["relation_type"]
        }
        MOCK_GRAPH_RELATIONS.append(new_relation)

        return {
            "success": True,
            "message": f"关系 '{new_relation['source']} → {new_relation['target']}' 已添加",
            "entity": new_relation
        }

    elif action == "DELETE_NODE":
        MOCK_GRAPH_NODES[:] = [n for n in MOCK_GRAPH_NODES if n["id"] != data["id"]]

        return {
            "success": True,
            "message": f"节点 '{data['id']}' 已删除"
        }

    elif action == "DELETE_RELATION":
        MOCK_GRAPH_RELATIONS[:] = [
            r for r in MOCK_GRAPH_RELATIONS
            if not (r["source"] == data["source"] and r["target"] == data["target"])
        ]

        return {
            "success": True,
            "message": f"关系已删除"
        }

    else:
        raise HTTPException(status_code=400, detail=f"不支持的操作: {action}")


@router.get("/export")
async def export_graph():
    """导出图谱数据（JSON格式）."""
    return {
        "nodes": MOCK_GRAPH_NODES,
        "relations": MOCK_GRAPH_RELATIONS,
        "metadata": {
            "version": "1.0",
            "exported_at": "2026-02-05"
        }
    }


@router.post("/import")
async def import_graph(data: dict):
    """导入图谱数据."""
    nodes = data.get("nodes", [])
    relations = data.get("relations", [])

    # 模拟导入
    MOCK_GRAPH_NODES.extend(nodes)
    MOCK_GRAPH_RELATIONS.extend(relations)

    return {
        "success": True,
        "message": f"已导入 {len(nodes)} 个节点和 {len(relations)} 条关系",
        "stats": {
            "nodes_added": len(nodes),
            "relations_added": len(relations)
        }
    }
