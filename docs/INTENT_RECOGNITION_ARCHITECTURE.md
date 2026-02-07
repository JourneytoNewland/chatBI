# 企业级意图识别架构方案

## 一、当前方案的局限性

### 现有实现（基于规则）
```python
# 当前方法：正则表达式匹配
TIME_PATTERNS = [
    (r'最近(\d+)[天日]', TimeGranularity.DAY, -1),
    (r'本月', TimeGranularity.MONTH, 0),
]
```

**主要问题：**
1. ❌ **扩展性差** - 每个新意图需要手动添加规则
2. ❌ **泛化能力弱** - 无法处理未见过的表达方式
3. ❌ **无语义理解** - "GMV的销售额" 无法识别为重复表达
4. ❌ **缺乏上下文** - 多轮对话无法理解指代
5. ❌ **维护成本高** - 规则冲突难以调试

---

## 二、业界最佳实践：三层混合架构

### 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                   用户查询输入                            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   L1: 快速规则匹配     │  ← 10% 常见查询（ms级）
         │   - 精确匹配           │
         │   - 简单正则           │
         │   - 同义词字典         │
         └───────────┬───────────┘
                     │ 未匹配
                     ▼
         ┌───────────────────────┐
         │   L2: 语义向量匹配     │  ← 60% 查询（10ms级）
         │   - Embedding模型      │
         │   - 向量检索 (Qdrant)  │
         │   - 相似度计算         │
         └───────────┬───────────┘
                     │ 低置信度
                     ▼
         ┌───────────────────────┐
         │   L3: LLM深度理解     │  ← 30% 复杂查询（100ms级）
         │   - Few-shot推理      │
         │   - 思维链（CoT）      │
         │   - 结构化输出         │
         └───────────┬───────────┘
                     │
                     ▼
            ┌────────────────┐
            │   意图融合      │
            │   - 置信度加权  │
            │   - 结果去重    │
            └────────┬────────┘
                     │
                     ▼
              ┌─────────────┐
              │  可视化面板  │
              │  - 解析过程  │
              │  - 置信度    │
              │  - 候选指标  │
              └─────────────┘
```

---

## 三、核心技术方案

### 3.1 LLM增强意图识别

#### 方案A：云端LLM（生产环境推荐）
```python
# 使用 OpenAI GPT-4 或 Claude
INTENT_RECOGNITION_PROMPT = """
你是一个专业的BI查询意图识别专家。

## 任务
分析用户查询，提取结构化意图信息。

## 输入
查询: {query}

## 输出格式（JSON）
{
    "core_query": "核心指标名",
    "time_range": {
        "start": "2024-01-01",
        "end": "2024-01-31"
    },
    "time_granularity": "day|week|month|quarter|year",
    "aggregation_type": "sum|avg|count|max|min|rate|ratio",
    "dimensions": ["地区", "品类"],
    "comparison_type": "yoy|mom|dod|wow",
    "filters": {"domain": "电商"},
    "confidence": 0.95,
    "reasoning": "推理过程"
}

## 示例
查询: "最近7天按地区的GMV总和"
输出: {
    "core_query": "GMV",
    "time_range": {"start": "2024-01-25", "end": "2024-02-01"},
    "time_granularity": "day",
    "aggregation_type": "sum",
    "dimensions": ["地区"],
    "comparison_type": null,
    "filters": {},
    "confidence": 0.98,
    "reasoning": "识别到时间词'最近7天'，维度'按地区'，聚合词'总和'，核心指标'GMV'"
}

请分析以下查询并输出JSON：
"""
```

**优势：**
- ✅ 准确率最高（95%+）
- ✅ 泛化能力强
- ✅ 支持复杂推理
- ✅ 易于维护（Prompt调优）

**劣势：**
- ⚠️ 成本较高（$0.01-0.03/次）
- ⚠️ 延迟较高（1-3秒）
- ⚠️ 数据隐私风险

---

#### 方案B：本地小模型（性价比推荐）
```python
# 使用 Qwen2.5-7B-Instruct 或 Llama-3-8B
# 优势：
# - 免费
# - 低延迟（<500ms）
# - 数据私有
# - 准确率可达85-90%

from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-7B-Instruct",
    device_map="auto",
    load_in_4bit=True  # 量化降低显存
)
```

---

### 3.2 语义向量增强

#### 当前方案升级
```python
# 问题：m3e-base (768维) 对专业领域理解不够
# 解决：使用更强的embedding模型

from sentence_transformers import SentenceTransformer

# 选项1: BGE-M3 (多语言，8192维)
embedder = SentenceTransformer('BAAI/bge-m3')

# 选项2: GTE-QueryEncoder (查询优化)
embedder = SentenceTransformer('thenlper/gte-large-zh')

# 选项3: OpenAI text-embedding-3 (云端)
from openai import OpenAI
client.embeddings.create(
    model="text-embedding-3-large",  # 3072维
    input="最近7天的GMV",
    dimensions=1024  # 可降维
)
```

---

### 3.3 知识图谱增强

#### 当前图谱扩展
```cypher
// 问题：当前图谱只有基础关系
// 解决：增加语义关系和规则

// 1. 添加同义词关系
CREATE (m:Metric {name: 'GMV'})-[:SYNONYM]->(成交金额)
CREATE (m)-[:SYNONYM]->(交易总额)
CREATE (m)-[:RELATED_TO]->(销售额)  // 相关词

// 2. 添加计算规则
CREATE (m)-[:CALCULATED_BY]->(
    Formula {expression: 'SUM(order_amount)'}
)

// 3. 添加领域约束
CREATE (m)-[:BELONGS_TO]->(Domain {name: '电商'})

// 4. 添加使用示例
CREATE (m)-[:EXAMPLE]->(Query {text: '最近7天的GMV'})
```

#### 图谱辅助意图识别
```python
def enhance_with_kg(query: str, intent: QueryIntent) -> QueryIntent:
    """使用知识图谱增强意图识别"""

    # 1. 在图谱中搜索查询词
    matches = graph.query(
        "MATCH (m:Metric) WHERE $query IN m.name OR $query IN m.synonyms RETURN m",
        query=intent.core_query
    )

    # 2. 提取相关约束
    for metric in matches:
        intent.filters['domain'] = metric.domain
        intent.filters['formula'] = metric.formula

    # 3. 发现隐含意图
    if "增长" in query and "率" in query:
        intent.aggregation_type = AggregationType.RATE
        intent.comparison_type = "yoy"

    return intent
```

---

### 3.4 Few-Shot Learning + RAG

```python
# 方案：检索相似查询作为示例

def few_shot_intent_recognition(query: str) -> QueryIntent:
    # 1. 检索相似历史查询（从Qdrant）
    similar_queries = qdrant.search(
        query_vector=embed(query),
        collection_name="query_history",
        top_k=3
    )

    # 2. 构造Few-shot示例
    examples = "\n".join([
        f"查询: {q.payload['query']}\n"
        f"意图: {q.payload['intent']}\n"
        for q in similar_queries
    ])

    # 3. 调用LLM
    prompt = f"""
参考以下示例，识别新查询的意图：

{examples}

新查询: {query}
意图:
"""

    return llm_call(prompt)
```

---

## 四、可视化方案

### 4.1 前端可视化面板

```typescript
// 显示内容
interface IntentVisualization {
    // 1. 查询解析过程
    parsingSteps: {
        stage: string        // "规则匹配" | "向量检索" | "LLM推理"
        result: any
        confidence: number
        duration: number
    }[]

    // 2. 意图卡片（7维）
    intentCard: {
        coreQuery: string
        timeRange: DateRange
        timeGranularity: string
        aggregationType: string
        dimensions: string[]
        comparisonType: string
        filters: Record<string, any>
    }

    // 3. 候选指标排序
    candidateMetrics: {
        name: string
        score: number          // 相似度分数
        matchReason: string    // 匹配原因说明
        formula: string
    }[]

    // 4. 知识图谱子图
    kgSubgraph: {
        nodes: Node[]          // 相关指标、维度、领域
        relations: Relation[]  // 语义关系
    }

    // 5. 置信度热力图
    confidenceHeatmap: {
        layer: string          // 规则/向量/LLM
        confidence: number
    }[]
}
```

### 4.2 后端可视化数据

```python
@app.post("/api/v1/search-with-debug")
async def search_with_debug(request: SearchRequest):
    """带调试信息的搜索接口"""

    # 1. 记录每层结果
    layer_results = {
        "rule_based": None,
        "semantic": None,
        "llm": None
    }

    # L1: 规则匹配
    start = time.time()
    result_rule = rule_matcher.match(request.query)
    layer_results["rule_based"] = {
        "matched": result_rule is not None,
        "confidence": result_rule.confidence if result_rule else 0,
        "duration": time.time() - start
    }

    if result_rule and result_rule.confidence > 0.9:
        return {"source": "rule", "result": result_rule, "debug": layer_results}

    # L2: 语义向量匹配
    start = time.time()
    result_semantic = semantic_search(request.query)
    layer_results["semantic"] = {
        "candidates": result_semantic[:3],
        "top_score": result_semantic[0].score if result_semantic else 0,
        "duration": time.time() - start
    }

    if result_semantic and result_semantic[0].score > 0.85:
        return {"source": "semantic", "result": result_semantic, "debug": layer_results}

    # L3: LLM深度推理
    start = time.time()
    result_llm = llm_intent_recognition(request.query)
    layer_results["llm"] = {
        "reasoning": result_llm.reasoning,
        "confidence": result_llm.confidence,
        "duration": time.time() - start
    }

    return {"source": "llm", "result": result_llm, "debug": layer_results}
```

---

## 五、评估与反馈机制

### 5.1 离线评估指标

```python
# 评估数据集构建
EVALUATION_DATASET = [
    {"query": "GMV", "expected": {"core_query": "GMV"}},
    {"query": "最近7天的GMV", "expected": {"core_query": "GMV", "time_range": "7d"}},
    {"query": "按地区的销售额", "expected": {"dimensions": ["地区"]}},
    # ... 1000+ 样本
]

# 评估指标
def evaluate_intent_recognition(model, dataset):
    metrics = {
        "accuracy": 0,      # 准确率
        "precision": 0,     # 精确率
        "recall": 0,        # 召回率
        "f1": 0,           # F1分数
        "latency_p50": 0,  # 延迟中位数
        "latency_p99": 0,  # P99延迟
    }
    return metrics
```

### 5.2 在线反馈学习

```python
# 用户反馈收集
@app.post("/api/v1/feedback")
async def collect_feedback(feedback: Feedback):
    """收集用户反馈用于持续优化"""

    # 保存到数据库
    db.save({
        "query": feedback.query,
        "predicted_intent": feedback.predicted,
        "correct_intent": feedback.correct,
        "user_id": feedback.user_id,
        "timestamp": datetime.now()
    })

    # 定期重训练模型
    if should_retrain():
        retrain_model()

    return {"status": "recorded"}
```

---

## 六、实施路线图

### Phase 1: 基础升级（1-2周）
- [ ] 升级embedding模型到 BGE-M3
- [ ] 扩展同义词词典（1000+）
- [ ] 优化规则引擎性能

### Phase 2: 语义增强（2-3周）
- [ ] 集成Qdrant语义检索
- [ ] 扩展知识图谱（关系、规则）
- [ ] 实现Few-shot检索

### Phase 3: LLM集成（2-4周）
- [ ] 接入OpenAI API或本地模型
- [ ] 实现三层混合架构
- [ ] 性能优化（缓存、批处理）

### Phase 4: 可视化（1-2周）
- [ ] 前端意图可视化面板
- [ ] 知识图谱可视化
- [ ] 置信度热力图

### Phase 5: 评估优化（持续）
- [ ] 构建评估数据集
- [ ] A/B测试框架
- [ ] 用户反馈收集

---

## 七、技术栈推荐

### 生产环境
```yaml
LLM:
  - OpenAI GPT-4o (云端, $0.005/1K tokens)
  - Claude 3.5 Sonnet (云端, $0.003/1K tokens)

Embedding:
  - text-embedding-3-large (3072维, $0.00013/1K tokens)
  - BGE-M3 (本地, 免费)

Vector DB:
  - Qdrant (已部署)

Graph DB:
  - Neo4j (已部署)

API框架:
  - FastAPI (已使用)

监控:
  - Prometheus + Grafana
```

### 本地开发
```yaml
LLM: Ollama (Qwen2.5-7B-Instruct)
Embedding: Sentence-Transformers (BGE-M3)
Vector: Qdrant
Graph: Neo4j
```

---

## 八、成本对比

| 方案 | 准确率 | 延迟 | 成本 | 复杂度 |
|------|--------|------|------|--------|
| 当前规则 | 60% | <10ms | $0 | 低 |
| 规则+向量 | 80% | ~50ms | $0 | 中 |
| 三层混合 | 95% | ~500ms | $0.01/次 | 高 |
| 纯LLM | 98% | ~2s | $0.03/次 | 低 |

**推荐策略：**
- 开发测试：本地小模型（免费）
- 生产环境：三层混合（成本可控，性能最优）

---

## 九、下一步行动

1. **立即实施**：
   - 升级embedding模型到BGE-M3
   - 扩展同义词词典
   - 优化规则匹配逻辑

2. **短期目标**（1周内）：
   - 实现LLM意图识别模块
   - 构建三层混合架构
   - 添加可视化调试接口

3. **长期目标**（1月内）：
   - 完整的可视化面板
   - 评估与反馈系统
   - 持续优化机制

---

**总结：当前规则方法只是起点，真正的生产系统需要三层混合架构 + 可视化 + 持续优化。**
