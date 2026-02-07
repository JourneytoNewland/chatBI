# ChatBI API 服务详细文档

**版本**: v0.1.0
**基础URL**: `http://localhost:8000`
**更新日期**: 2025-02-05

---

## 📑 目录

1. [主搜索API](#1-主搜索api)
2. [数据管理API](#2-数据管理api)
3. [Debug API（新版）](#3-debug-api新版)
4. [图谱管理API](#4-图谱管理api)
5. [智能查询API v2](#5-智能查询api-v2)
6. [健康检查](#6-健康检查)

---

## 1. 主搜索API

**基础路径**: `/api/v1`
**文件**: [src/api/routes.py](src/api/routes.py)

### 1.1 语义检索

**端点**: `POST /api/v1/search`

**功能**: 基于向量相似度和知识图谱的混合语义检索

#### 输入参数

```json
{
  "query": "GMV上升趋势前10名",
  "top_k": 10,
  "score_threshold": 0.3,
  "conversation_id": "session_12345"
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | `string` | ✅ | - | 自然语言查询文本 |
| `top_k` | `integer` | ❌ | `10` | 返回结果数量（1-100） |
| `score_threshold` | `float` | ❌ | `null` | 相似度阈值（0.0-1.0） |
| `conversation_id` | `string` | ❌ | `null` | 会话ID，用于多轮对话 |

#### 输出格式

```json
{
  "query": "GMV上升趋势前10名",
  "intent": {
    "core_query": "GMV",
    "time_range": ["2024-01-26", "2025-02-05"],
    "time_granularity": "day",
    "aggregation_type": null,
    "dimensions": [],
    "comparison_type": null,
    "trend_type": "upward",
    "sort_requirement": {
      "top_n": 10,
      "order": "desc"
    },
    "threshold_filters": []
  },
  "candidates": [
    {
      "metric_id": "metric_001",
      "name": "GMV",
      "code": "gmv",
      "description": "商品交易总额（Gross Merchandise Volume）",
      "domain": "电商",
      "synonyms": ["成交金额", "总成交额"],
      "importance": 0.95,
      "vector_score": 0.89,
      "graph_score": 0.75,
      "final_score": 0.864,
      "source": "vector"
    }
  ],
  "total": 1,
  "execution_time": 156.78,
  "conversation_id": "session_12345"
}
```

#### 输出字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `query` | `string` | 原始查询 |
| `intent.core_query` | `string` | 提取的核心查询词 |
| `intent.trend_type` | `string` | 趋势类型：`upward`/`downward`/`fluctuating`/`stable` |
| `candidates[]` | `array` | 候选指标列表 |
| `candidates[].final_score` | `float` | 最终得分（0-1） |
| `total` | `integer` | 返回结果数量 |
| `execution_time` | `float` | 执行时间（毫秒） |

#### 示例

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "最近7天的DAU",
    "top_k": 5
  }'
```

---

## 2. 数据管理API

**基础路径**: `/api/v1/management`
**文件**: [src/api/management_api.py](src/api/management_api.py)

### 2.1 批量导入指标

**端点**: `POST /api/v1/management/metrics/batch-import`

#### 输入参数

```json
{
  "metrics": [
    {
      "name": "GMV",
      "code": "gmv",
      "description": "商品交易总额",
      "domain": "电商",
      "synonyms": ["成交金额", "总成交额"],
      "importance": 0.95,
      "formula": "SUM(order_amount)"
    }
  ]
}
```

#### 输出格式

```json
{
  "success": true,
  "imported": 1,
  "failed": 0,
  "task_id": "task_abc123",
  "message": "成功导入 1 个指标"
}
```

#### 任务状态查询

**端点**: `GET /api/v1/management/tasks/{task_id}`

```json
{
  "task_id": "task_abc123",
  "status": "completed",
  "progress": 100,
  "imported": 1,
  "failed": 0,
  "error": null
}
```

---

### 2.2 查询单个指标

**端点**: `GET /api/v1/management/metrics/{metric_id}`

#### 输入参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `metric_id` | `string` | 指标ID（路径参数） |

#### 输出格式

```json
{
  "metric_id": "metric_001",
  "name": "GMV",
  "code": "gmv",
  "description": "商品交易总额",
  "domain": "电商",
  "synonyms": ["成交金额"],
  "importance": 0.95,
  "formula": "SUM(order_amount)",
  "created_at": "2025-01-15T10:30:00",
  "updated_at": "2025-01-15T10:30:00"
}
```

---

### 2.3 生成指标摘要

**端点**: `POST /api/v1/management/metrics/{metric_id}/summary`

#### 输入参数

```json
{
  "use_llm": true
}
```

#### 输出格式

```json
{
  "metric_id": "metric_001",
  "summary": "GMV（Gross Merchandise Volume）是电商核心指标，表示商品交易总额...",
  "model": "glm-4-flash",
  "tokens_used": 256
}
```

---

## 3. Debug API（新版）⭐

**基础路径**: `/debug`
**文件**: [src/api/debug_routes.py](src/api/debug_routes.py)

### 3.1 执行链路完整追踪

**端点**: `POST /debug/search-debug`

**功能**: 返回查询执行的完整链路，包括每步的输入、算法、输出

#### 输入参数

```json
{
  "query": "GMV上升趋势前10名",
  "top_k": 3,
  "score_threshold": 0.3
}
```

#### 输出格式

```json
{
  "query": "GMV上升趋势前10名",
  "total_duration_ms": 15739.45,
  "execution_steps": [
    {
      "step_name": "意图识别",
      "step_type": "intent_recognition",
      "duration_ms": 2.27,
      "success": true,
      "input_data": {
        "原始查询": "GMV上升趋势前10名",
        "解析后查询": "GMV上升趋势前10名",
        "会话ID": "1770275921",
        "会话轮次": 0
      },
      "algorithm": "意图识别算法：\n1. 正则表达式匹配\n   - 时间范围：(?P<数字>\\d+)\\s*(天|日|周|月|年)\n   - 趋势分析：(GMV|DAU|营收).{0,5}(上升|增长)\n   - 排序需求：(前|Top|top)\\s*(\\d+)",
      "algorithm_params": {
        "模型": "规则引擎 + 正则表达式",
        "支持意图": ["时间范围", "聚合类型", "趋势", "排序"]
      },
      "output_data": {
        "core_query": "GMV上升趋势前10名",
        "trend_type": "upward",
        "sort_requirement": {
          "top_n": 10,
          "order": "desc"
        }
      }
    },
    {
      "step_name": "LLM意图识别",
      "step_type": "llm_intent_recognition",
      "duration_ms": 7195.96,
      "success": true,
      "input_data": {
        "原始查询": "GMV上升趋势前10名",
        "LLM模型": "glm-4-flash",
        "API配置状态": "已配置"
      },
      "algorithm": "LLM意图识别算法（智谱AI）：\n模型：glm-4-flash\n方法：Few-shot Learning + Chain of Thought\n\n实际提示词（部分截取）：\n你是一个专业的BI查询意图识别专家...",
      "algorithm_params": {
        "模型": "glm-4-flash",
        "Temperature": 0.1,
        "Top_P": 0.7
      },
      "output_data": {
        "识别结果": {
          "core_query": "GMV",
          "confidence": 0.85,
          "reasoning": "识别到核心指标GMV，但查询中未包含时间范围...",
          "model": "glm-4-flash",
          "tokens_used": {
            "prompt_tokens": 860,
            "completion_tokens": 106,
            "total_tokens": 966
          }
        },
        "规则引擎vs LLM对比": {
          "规则引擎核心查询": "GMV上升趋势前10名",
          "LLM核心查询": "GMV",
          "是否一致": false,
          "规则引擎趋势": "upward",
          "LLM置信度": 0.85
        }
      }
    },
    {
      "step_name": "查询向量化",
      "step_type": "vectorization",
      "duration_ms": 9373.43,
      "input_data": {
        "查询文本": "GMV上升趋势前10名",
        "模型": "sentence-transformers/all-MiniLM-L6-v2"
      },
      "output_data": {
        "向量形状": "(384,)",
        "向量范数": 1.0
      }
    },
    {
      "step_name": "向量召回",
      "step_type": "vector_recall",
      "duration_ms": 6.12,
      "input_data": {
        "链路": "双路召回链路1",
        "查询向量": "shape=(384,)",
        "召回策略": "top_k=6, threshold=None"
      },
      "output_data": {
        "召回数量": 6,
        "top_5候选": [
          {"name": "GMV", "score": 0.8934, "id": "metric_001"},
          {"name": "成交金额", "score": 0.8756, "id": "metric_002"}
        ]
      }
    },
    {
      "step_name": "图谱召回",
      "step_type": "graph_recall",
      "duration_ms": 0.00,
      "input_data": {
        "链路": "双路召回链路2",
        "查询": "GMV上升趋势前10名",
        "图数据库": "Neo4j"
      },
      "output_data": {
        "召回数量": 0
      }
    },
    {
      "step_name": "双路合并",
      "step_type": "merge_dual_path",
      "duration_ms": 0.01,
      "input_data": {
        "向量召回数量": 6,
        "图谱召回数量": 0
      },
      "output_data": {
        "合并后数量": 6,
        "去重数量": 0
      }
    },
    {
      "step_name": "特征提取",
      "step_type": "feature_extraction",
      "duration_ms": 0.09,
      "input_data": {
        "候选数量": 6
      },
      "algorithm": "特征提取算法（11维特征）：\n1. 向量相似度 (weight: 0.30)\n2. 图谱分数 (weight: 0.15)\n..."
    },
    {
      "step_name": "精排打分",
      "step_type": "reranking",
      "duration_ms": 0.07,
      "output_data": {
        "排名结果": [
          {"name": "GMV", "score": 0.864, "rank": 1},
          {"name": "成交金额", "score": 0.821, "rank": 2}
        ]
      }
    },
    {
      "step_name": "结果验证",
      "step_type": "validation",
      "duration_ms": 0.03,
      "output_data": {
        "通过数量": 3,
        "拒绝数量": 0
      }
    }
  ],
  "final_result": {
    "query": "GMV上升趋势前10名",
    "total": 3,
    "candidates": [...]
  }
}
```

#### 执行步骤说明

| 步骤 | 名称 | 说明 | 平均耗时 |
|------|------|------|----------|
| 1 | 意图识别 | 规则引擎提取查询意图 | < 5ms |
| 2 | **LLM意图识别** | 智谱AI大模型识别 | ~7秒 |
| 3 | 查询向量化 | 转换为向量（首次加载慢） | ~9秒 |
| 4 | 向量召回 | 双路链路1 - 语义检索 | 20-50ms |
| 5 | 图谱召回 | 双路链路2 - 关系推理 | < 10ms |
| 6 | 双路合并 | 合并两个链路结果 | < 1ms |
| 7 | 特征提取 | 提取11维特征 | < 1ms |
| 8 | 精排打分 | 加权求和排序 | < 1ms |
| 9 | 结果验证 | 规则验证 | < 1ms |

#### 示例

```bash
curl -X POST http://localhost:8000/debug/search-debug \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "DAU大于10000",
    "top_k": 3
  }' | jq '.execution_steps[] | {step: .step_name, duration: .duration_ms}'
```

---

## 4. 图谱管理API 🕸️

**基础路径**: `/api/v1/graph`
**文件**: [src/api/graph_endpoints.py](src/api/graph_endpoints.py)

### 4.1 查询所有节点

**端点**: `GET /api/v1/graph/nodes`

#### 输出格式

```json
{
  "nodes": [
    {
      "id": "metric_001",
      "labels": ["Metric"],
      "properties": {
        "name": "GMV",
        "code": "gmv",
        "description": "商品交易总额",
        "domain": "电商"
      }
    },
    {
      "id": "domain_001",
      "labels": ["Domain"],
      "properties": {
        "name": "电商",
        "description": "电子商务业务域"
      }
    }
  ],
  "total": 2
}
```

---

### 4.2 查询所有关系

**端点**: `GET /api/v1/graph/relations`

#### 输出格式

```json
{
  "relations": [
    {
      "id": "rel_001",
      "type": "BELONGS_TO",
      "source": "metric_001",
      "target": "domain_001",
      "properties": {
        "confidence": 0.95,
        "created_at": "2025-01-15"
      }
    }
  ],
  "total": 1
}
```

---

### 4.3 图谱统计

**端点**: `GET /api/v1/graph/statistics`

#### 输出格式

```json
{
  "nodes": {
    "total": 150,
    "by_type": {
      "Metric": 120,
      "Domain": 15,
      "Category": 15
    }
  },
  "relations": {
    "total": 280,
    "by_type": {
      "BELONGS_TO": 120,
      "CORRELATED_WITH": 100,
      "CALCULATED_BY": 60
    }
  },
  "density": 0.025,
  "connected_components": 1
}
```

---

### 4.4 编辑图谱

**端点**: `POST /api/v1/graph/edit`

#### 输入参数

```json
{
  "action": "add_node",
  "data": {
    "id": "metric_123",
    "labels": ["Metric"],
    "properties": {
      "name": "新增指标",
      "code": "new_metric",
      "description": "这是一个新指标"
    }
  }
}
```

支持的操作：
- `add_node`: 添加节点
- `update_node`: 更新节点
- `delete_node`: 删除节点
- `add_relation`: 添加关系
- `delete_relation`: 删除关系

---

## 5. 智能查询API v2 🧠

**基础路径**: `/api/v2`
**文件**: [src/api/v2_query_api.py](src/api/v2_query_api.py)

### 5.1 增强版查询

**端点**: `POST /api/v2/query`

#### 输入参数

```json
{
  "query": "最近30天GMV的日趋势",
  "top_k": 10,
  "enable_llm": true,
  "enable_graph": true
}
```

#### 输出格式

```json
{
  "query": "最近30天GMV的日趋势",
  "intent": {
    "core_query": "GMV",
    "time_range": ["2025-01-06", "2025-02-05"],
    "time_granularity": "day",
    "trend_type": null
  },
  "analysis": {
    "has_trend": true,
    "trend_direction": "upward",
    "trend_strength": 0.78,
    "insights": [
      "GMV在过去30天呈上升趋势",
      "平均增长率约为15%"
    ]
  },
  "candidates": [...],
  "total": 3,
  "execution_time": 245.67
}
```

---

### 5.2 深度分析

**端点**: `POST /api/v2/analyze`

#### 输入参数

```json
{
  "query": "为什么GMV下降了",
  "metric_id": "metric_001",
  "time_range": "last_7_days"
}
```

#### 输出格式

```json
{
  "analysis_type": "root_cause",
  "metric": "GMV",
  "findings": [
    {
      "factor": "用户活跃度下降",
      "impact": "high",
      "confidence": 0.82
    },
    {
      "factor": "客单价降低",
      "impact": "medium",
      "confidence": 0.65
    }
  ],
  "recommendations": [
    "建议开展用户召回活动",
    "优化商品推荐算法"
  ],
  "model": "glm-4-flash",
  "latency_ms": 3456.78
}
```

---

## 6. 健康检查

**端点**: `GET /health`

### 输出格式

```json
{
  "status": "healthy",
  "service": "Semantic Query System",
  "version": "0.1.0"
}
```

---

## 📊 完整API清单汇总

| 序号 | API服务 | 端点数 | 前缀 | 核心功能 |
|------|--------|--------|------|----------|
| 1 | 主搜索API | 1 | `/api/v1` | 语义检索 |
| 2 | 数据管理API | 6 | `/api/v1/management` | 指标CRUD、批量导入 |
| 3 | Debug API（新版） | 1 | `/debug` | 执行链路追踪 ⭐ |
| 4 | Debug API（旧版） | 3 | `/api/v1/debug` | 意图可视化（已弃用） |
| 5 | 图谱管理API | 8 | `/api/v1/graph` | 节点/关系管理 |
| 6 | 智能查询API v2 | 7 | `/api/v2` | 增强版查询 |
| 7 | 健康检查 | 1 | `/` | 系统状态 |
| **总计** | **7个服务** | **27个端点** | - | - |

---

## 🔧 错误码

| 状态码 | 说明 | 示例 |
|--------|------|------|
| 200 | 成功 | API调用成功 |
| 400 | 请求参数错误 | query字段缺失 |
| 404 | 资源不存在 | 指标ID不存在 |
| 422 | 参数验证失败 | top_k超出范围 |
| 500 | 服务器内部错误 | 后端异常 |

---

## 📝 使用示例

### Python示例

```python
import httpx

# 1. 语义检索
response = httpx.post(
    "http://localhost:8000/api/v1/search",
    json={"query": "GMV上升趋势前10名", "top_k": 5}
)
data = response.json()
print(f"找到 {data['total']} 个候选指标")

# 2. Debug API - 查看执行链路
response = httpx.post(
    "http://localhost:8000/debug/search-debug",
    json={"query": "DAU大于10000", "top_k": 3}
)
steps = response.json()["execution_steps"]
for step in steps:
    print(f"{step['step_name']}: {step['duration_ms']:.2f}ms")

# 3. 图谱查询
response = httpx.get("http://localhost:8000/api/v1/graph/nodes")
nodes = response.json()["nodes"]
print(f"图谱共有 {len(nodes)} 个节点")
```

### JavaScript示例

```javascript
// 语义检索
const response = await fetch('http://localhost:8000/api/v1/search', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    query: '最近7天的DAU',
    top_k: 5
  })
});
const data = await response.json();
console.log(`找到 ${data.total} 个候选指标`);

// Debug API
const debugResponse = await fetch('http://localhost:8000/debug/search-debug', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    query: 'GMV上升趋势',
    top_k: 3
  })
});
const debugData = await debugResponse.json();
console.log(`总耗时: ${debugData.total_duration_ms}ms`);
```

---

**文档更新**: 2025-02-05
**联系方式**: 见项目README
