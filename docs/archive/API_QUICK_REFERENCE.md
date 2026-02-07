# ChatBI API 输入输出快速参考

**版本**: v0.1.0
**更新**: 2025-02-05

---

## 🚀 快速查询表

### 核心API速查

| API | 方法 | 端点 | 主要输入 | 主要输出 |
|-----|------|------|----------|----------|
| **语义检索** | POST | `/api/v1/search` | `query`, `top_k` | `candidates`, `intent` |
| **执行链路** | POST | `/debug/search-debug` | `query`, `top_k` | `execution_steps[9]` |
| **图谱节点** | GET | `/api/v1/graph/nodes` | - | `nodes[]` |
| **图谱关系** | GET | `/api/v1/graph/relations` | - | `relations[]` |
| **批量导入** | POST | `/api/v1/management/metrics/batch-import` | `metrics[]` | `task_id` |
| **增强查询** | POST | `/api/v2/query` | `query`, `enable_llm` | `analysis` |

---

## 📋 详细输入输出

### 1. 语义检索 API

#### 输入

| 字段 | 类型 | 必填 | 示例 | 说明 |
|------|------|------|------|------|
| `query` | `string` | ✅ | `"GMV上升趋势"` | 自然语言查询 |
| `top_k` | `int` | ❌ | `10` | 返回数量（1-100） |
| `score_threshold` | `float` | ❌ | `0.3` | 相似度阈值 |
| `conversation_id` | `string` | ❌ | `"session_123"` | 会话ID |

#### 输出

```json
{
  "query": "GMV上升趋势",
  "candidates": [
    {
      "name": "GMV",
      "final_score": 0.89,
      "description": "商品交易总额"
    }
  ],
  "total": 1,
  "execution_time": 156.78
}
```

---

### 2. Debug API（执行链路） ⭐

#### 输入

```json
{
  "query": "GMV上升趋势前10名",
  "top_k": 3
}
```

#### 输出 - 9个执行步骤

| 步骤 | 字段 | 说明 |
|------|------|------|
| 1️⃣ 意图识别 | `duration_ms: 2.27` | 规则引擎，< 5ms |
| 2️⃣ **LLM意图识别** | `duration_ms: 7195` | 智谱AI，~7秒 |
| 3️⃣ 查询向量化 | `duration_ms: 9373` | 首次加载慢 |
| 4️⃣ 向量召回 | `duration_ms: 6.12` | 双路链路1 |
| 5️⃣ 图谱召回 | `duration_ms: 0.00` | 双路链路2 |
| 6️⃣ 双路合并 | `duration_ms: 0.01` | 合并结果 |
| 7️⃣ 特征提取 | `duration_ms: 0.09` | 11维特征 |
| 8️⃣ 精排打分 | `duration_ms: 0.07` | 加权排序 |
| 9️⃣ 结果验证 | `duration_ms: 0.03` | 规则验证 |

**关键字段**:
- `algorithm`: 实际使用的算法和提示词
- `input_data`: 真实的输入数据
- `output_data`: 真实的输出结果
- `tokens_used`: LLM使用的token数

---

### 3. 图谱管理 API

#### 3.1 查询节点

**输入**: 无（GET请求）

**输出**:
```json
{
  "nodes": [
    {
      "id": "metric_001",
      "name": "GMV",
      "domain": "电商"
    }
  ],
  "total": 1
}
```

#### 3.2 查询关系

**输入**: 无（GET请求）

**输出**:
```json
{
  "relations": [
    {
      "source": "metric_001",
      "target": "domain_001",
      "type": "BELONGS_TO"
    }
  ]
}
```

#### 3.3 编辑图谱

**输入**:
```json
{
  "action": "add_node",
  "data": {
    "name": "新指标",
    "type": "Metric"
  }
}
```

**输出**:
```json
{
  "success": true,
  "message": "节点添加成功"
}
```

---

### 4. 数据管理 API

#### 4.1 批量导入

**输入**:
```json
{
  "metrics": [
    {
      "name": "GMV",
      "code": "gmv",
      "description": "商品交易总额",
      "domain": "电商"
    }
  ]
}
```

**输出**:
```json
{
  "success": true,
  "imported": 1,
  "task_id": "task_abc123"
}
```

#### 4.2 查询任务状态

**输入**: `GET /api/v1/management/tasks/{task_id}`

**输出**:
```json
{
  "task_id": "task_abc123",
  "status": "completed",
  "progress": 100,
  "imported": 1,
  "failed": 0
}
```

---

### 5. 智能查询 API v2

#### 5.1 增强查询

**输入**:
```json
{
  "query": "最近30天GMV的日趋势",
  "enable_llm": true,
  "enable_graph": true
}
```

**输出**:
```json
{
  "query": "最近30天GMV的日趋势",
  "analysis": {
    "has_trend": true,
    "trend_direction": "upward",
    "insights": ["GMV呈上升趋势"]
  },
  "candidates": [...]
}
```

#### 5.2 深度分析

**输入**:
```json
{
  "query": "为什么GMV下降了",
  "metric_id": "metric_001",
  "time_range": "last_7_days"
}
```

**输出**:
```json
{
  "analysis_type": "root_cause",
  "findings": [
    {
      "factor": "用户活跃度下降",
      "impact": "high",
      "confidence": 0.82
    }
  ],
  "recommendations": [
    "建议开展用户召回活动"
  ]
}
```

---

## 🧪 测试命令

```bash
# 1. 语义检索
curl -X POST http://localhost:8000/api/v1/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"GMV","top_k":3}'

# 2. 执行链路追踪（含LLM）
curl -X POST http://localhost:8000/debug/search-debug \
  -H 'Content-Type: application/json' \
  -d '{"query":"GMV上升趋势前10名","top_k":3}'

# 3. 查询图谱节点
curl http://localhost:8000/api/v1/graph/nodes

# 4. 查询图谱关系
curl http://localhost:8000/api/v1/graph/relations

# 5. 图谱统计
curl http://localhost:8000/api/v1/graph/statistics

# 6. 健康检查
curl http://localhost:8000/health
```

---

## 📊 数据模型

### SearchRequest（检索请求）

```typescript
{
  query: string;           // 查询文本
  top_k?: number;         // 返回数量 (默认10)
  score_threshold?: number; // 相似度阈值
  conversation_id?: string; // 会话ID
}
```

### SearchResponse（检索响应）

```typescript
{
  query: string;
  intent: {
    core_query: string;
    time_range?: [Date, Date];
    trend_type?: 'upward' | 'downward' | 'fluctuating' | 'stable';
    sort_requirement?: { top_n: number; order: 'desc' | 'asc' };
  };
  candidates: Array<{
    metric_id: string;
    name: string;
    final_score: number;
    description: string;
  }>;
  total: number;
  execution_time: number;
}
```

### GraphNode（图谱节点）

```typescript
{
  id: string;
  labels: string[];
  properties: {
    name: string;
    code?: string;
    description?: string;
    domain?: string;
  };
}
```

---

**💡 提示**: 完整API文档见 [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
