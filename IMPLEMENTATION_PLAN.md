按开发指南要求，记录当前阶段的详细计划：

```markdown
## Phase 1: 向量召回基座

**目标**: 搭建可独立运行的向量语义检索服务
**成功标准**: 
- 召回率 ≥ 85%
- P99延迟 ≤ 50ms

### 任务分解

- [x] 1.1 项目骨架搭建
- [x] 1.2 向量化Pipeline
- [ ] 1.3 Qdrant部署与集成
- [ ] 1.4 检索API实现
- [ ] 1.5 测试用例编写
- [ ] 1.6 性能基准测试

### 当前任务: 1.3 Qdrant部署与集成
**状态**: 待开始
**预期输出**: QdrantVectorStore类，支持Collection创建、批量upsert、ANN检索
```

---

### Phase 1 与 Claude Code 协作详解

#### 任务 1.1: 项目骨架搭建

**与 Claude Code 的对话策略**：

```plaintext
我正在搭建一个语义检索系统的项目骨架。请帮我：

1. 创建项目目录结构（参考 CLAUDE.md 中的结构）
2. 生成 pyproject.toml，包含以下依赖：
   - fastapi, uvicorn
   - qdrant-client
   - sentence-transformers
   - pytest, pytest-asyncio
3. 创建基础的 __init__.py 文件
4. 设置 pre-commit hooks (black, ruff, mypy)

请一步步执行，每步完成后告诉我结果。
```

**预期 Claude Code 输出**：它会逐步创建文件，你可以实时审查每个文件的内容。

#### 任务 1.2: 向量化 Pipeline

**Prompt 模板**：

```plaintext
当前任务：实现 MetricVectorizer 类

需求：
1. 输入：指标元数据字典，包含 name, code, description, synonyms, domain, formula
2. 输出：768维向量

技术要求：
- 使用 sentence-transformers 加载 m3e-base 模型
- 将多个字段按模板拼接后生成向量
- 支持单条和批量向量化
- 添加类型注解和文档字符串

请先阅读现有代码结构，然后在 src/recall/vector/ 下创建 vectorizer.py

参考向量化模板：
"指标名称: {name}
指标编码: {code}
业务含义: {description}
同义词: {synonyms}
业务域: {domain}"
```

**代码审查要点**（让 Claude Code 帮你检查）：

```plaintext
请审查刚才生成的 MetricVectorizer 类：

1. 模型加载是否支持延迟初始化？（避免import时就加载）
2. 批量向量化是否有进度条？
3. 异常处理是否完善？
4. 是否有单元测试？

如果有问题请直接修复。
```

#### 任务 1.3: Qdrant 集成

**分步骤 Prompt**：

```plaintext
# Step 1: 创建 Qdrant 客户端封装
请在 src/recall/vector/ 下创建 qdrant_client.py

需求：
- 封装 Qdrant 连接管理
- 支持创建 Collection（HNSW索引，ef_construction=200, M=16）
- 支持批量 upsert
- 支持 ANN 检索，返回 Top-K

配置通过环境变量读取：QDRANT_HOST, QDRANT_PORT
```

```plaintext
# Step 2: 编写集成测试
请为 QdrantVectorStore 编写测试，使用 pytest fixtures：

测试场景：
1. 创建 Collection
2. 插入 10 条测试数据
3. 检索相似向量，验证返回结果数量
4. 清理测试数据

使用 Qdrant 的内存模式进行测试，避免依赖外部服务。
```

#### 任务 1.4: 检索 API

**TDD 方式的 Prompt**：

```plaintext
我们采用 TDD 方式实现检索 API。

Step 1: 先写测试
请在 tests/test_api/ 下创建 test_search.py

测试用例：
1. test_search_exact_match: 查询"GMV"应返回GMV指标在Top-1
2. test_search_synonym: 查询"成交总额"应返回GMV在Top-3
3. test_search_empty_query: 空查询应返回400错误
4. test_search_response_format: 验证返回结构包含 candidates, executionTime

使用 FastAPI TestClient 进行测试。
```

```plaintext
Step 2: 实现 API 使测试通过
现在请实现 src/api/search.py 使上述测试通过。

API 规格：
POST /api/v1/search
Request: {"query": "GMV", "top_k": 10}
Response: {
  "candidates": [...],
  "executionTime": "23ms"
}
```

---

### Phase 2 与 Claude Code 协作详解

#### 任务 2.1: 本体模型定义

**Prompt**：

```plaintext
请帮我设计 Neo4j 的本体模型。

实体类型：
1. Metric - 指标节点
2. Dimension - 维度节点  
3. BusinessDomain - 业务域节点

关系类型：
1. belongsToDomain: Metric -> BusinessDomain
2. hasDimension: Metric -> Dimension
3. derivedFrom: Metric -> Metric (带 confidence 属性)
4. correlatesWith: Metric -> Metric (带 weight 属性)

请生成：
1. Cypher 建模语句（创建约束和索引）
2. Python dataclass 定义（用于代码中操作）
3. 示例数据插入脚本（10个指标作为种子数据）

文件位置：src/recall/graph/schema.py 和 scripts/init_graph.cypher
```

#### 任务 2.2: 图谱数据导入

**批量导入 Prompt**：

```plaintext
请实现图谱数据批量导入功能。

输入格式（CSV）：
metrics.csv: metricId, metricName, metricCode, description, domain, importance
relations.csv: sourceId, targetId, relationType, weight

需求：
1. 解析 CSV 文件
2. 批量创建节点（使用 UNWIND 优化）
3. 批量创建关系
4. 支持增量更新（已存在的节点更新属性而非重复创建）
5. 导入进度显示

文件位置：src/recall/graph/importer.py
```

---

### Phase 3 与 Claude Code 协作详解

#### 任务 3.1: 双路召回框架

**Prompt**：

```plaintext
请实现双路召回的并行执行框架。

需求：
1. 向量召回和图谱召回并行执行
2. 使用 asyncio 实现并发
3. 设置超时机制（单路超时不影响另一路）
4. 结果合并去重（以 metricId 为 key）

接口定义：
async def dual_recall(
    query: str,
    query_vector: np.ndarray,
    vector_top_k: int = 50,
    graph_top_k: int = 30,
    timeout: float = 0.2  # 200ms
) -> List[Candidate]

请在 src/recall/dual_recall.py 实现
```

#### 任务 3.2: 特征工程

**逐个特征实现的 Prompt 模式**：

```plaintext
请实现精排层的特征提取器，采用策略模式设计。

先创建基类：
class FeatureExtractor(ABC):
    @abstractmethod
    def extract(self, candidate: Candidate, context: QueryContext) -> float:
        pass

然后逐个实现 11 个特征提取器：
1. VectorSimilarityExtractor - 余弦相似度
2. QueryCoverageExtractor - 查询词覆盖率
...

每实现一个，先写单元测试。

文件位置：src/rerank/features/
```

**调试困难时的 Prompt**：

```plaintext
query_coverage 特征的计算结果不符合预期。

输入：
- candidate.metricName = "GMV"
- candidate.synonyms = ["成交总额", "交易额"]
- query_tokens = ["最近", "7天", "GMV"]

期望输出：0.33（只覆盖了"GMV"）
实际输出：0.0

请帮我调试，找出问题原因并修复。
```

#### 任务 3.3: 规则打分器

**Prompt**：

```plaintext
请实现 RuleBasedRanker 类。

需求：
1. 支持配置化的特征权重
2. 权重配置从 YAML 文件读取
3. 输出不仅包含最终得分，还包含每个特征的得分明细（用于可解释性）
4. 添加单元测试

权重配置示例（configs/rerank_weights.yaml）：
weights:
  vector_similarity: 0.20
  query_coverage: 0.08
  ...

文件位置：src/rerank/ranker.py
```

---

### Phase 4 与 Claude Code 协作详解

#### 验证器实现

**Prompt**：

```plaintext
请实现本体验证器的框架。

设计要求：
1. 采用责任链模式，每个验证规则是一个 Validator
2. 验证结果分为 PASSED/WARNING/FAILED 三种状态
3. 支持规则的动态加载（从配置文件）
4. 每个规则可独立启用/禁用

基类：
@dataclass
class ValidationResult:
    status: ValidationStatus
    check_type: str
    message: str
    suggestion: Optional[str] = None

class Validator(ABC):
    @abstractmethod
    def validate(self, context: ValidationContext) -> ValidationResult:
        pass

请实现：
1. DimensionCompatibilityValidator
2. TimeGranularityValidator
3. DataFreshnessValidator
4. PermissionValidator

文件位置：src/validator/
```

---

### Phase 5 与 Claude Code 协作详解

#### LTR 模型训练

**Prompt**：

```plaintext
请实现 Learning to Rank 模型的训练 Pipeline。

需求：
1. 数据格式转换：将标注数据转为 XGBoost ranking 格式
2. 特征工程：复用 Phase 3 的特征提取器
3. 模型训练：使用 LambdaMART 目标函数
4. 评估指标：NDCG@10, MAP
5. 模型保存与加载

标注数据格式：
[
  {
    "query": "最近7天GMV",
    "candidates": [
      {"metricId": "m1", "label": 4},  // 4=完全相关
      {"metricId": "m2", "label": 2},
      ...
    ]
  }
]

文件位置：src/rerank/ltr/
```

---

### Claude Code 最佳实践总结

#### 1. Prompt 结构模板

每次与 Claude Code 交互时，使用以下结构：

```plaintext
【上下文】当前阶段、已完成的工作、相关文件
【任务】具体要做什么
【技术要求】类型注解、测试、文档等
【输出位置】文件路径
【验收标准】如何判断完成
```

#### 2. 增量迭代模式

不要一次性让 Claude Code 生成大量代码。推荐流程：

```plaintext
生成框架 → 审查 → 补充细节 → 测试 → 修复 → 下一个模块
```

#### 3. 遇到问题时的 Prompt

```plaintext
【问题描述】具体的错误信息或不符合预期的行为
【复现步骤】输入是什么、期望输出是什么、实际输出是什么
【已尝试的方案】做过哪些尝试
【请求】帮我分析原因并修复
```

#### 4. 代码审查 Prompt

```plaintext
请审查 {文件路径} 的代码：

检查点：
1. 是否有类型注解遗漏？
2. 异常处理是否完善？
3. 是否有潜在的性能问题？
4. 是否符合项目代码规范？
5. 测试覆盖是否充分？

发现问题请直接修复。
```

#### 5. 重构 Prompt

```plaintext
{文件路径} 的代码已经能工作，但我觉得可以更好。

请帮我重构：
1. 提取重复逻辑为独立函数
2. 优化函数签名，减少参数数量
3. 添加更好的注释
4. 如果有更 Pythonic 的写法，请改进

保持功能不变，确保测试仍然通过。
```

---

### Claude Code 与 Git 工作流集成

#### 分支策略

```plaintext
main
 └── develop
      ├── feature/phase1-vector-recall
      ├── feature/phase2-graph-infra
      ├── feature/phase3-dual-recall
      └── ...
```

#### Commit 消息规范

让 Claude Code 帮你生成规范的 commit 消息：

```plaintext
请为当前的改动生成 commit 消息，使用 conventional commits 格式：

类型：feat/fix/refactor/test/docs
范围：vector-recall/graph/rerank/validator/api
描述：简短说明做了什么

示例：feat(vector-recall): implement MetricVectorizer with m3e-base model
```

#### PR 描述生成

```plaintext
请为这个 feature 分支生成 PR 描述：

包含：
1. 实现了什么功能
2. 主要改动文件
3. 如何测试
4. 关联的任务编号
```

---

### 每日工作流建议

**开始工作时**：

```plaintext
我今天要继续 {当前任务}。

请帮我：
1. 回顾 IMPLEMENTATION_PLAN.md 的当前状态
2. 列出今天要完成的具体子任务
3. 确认需要的上下文文件
```

**结束工作时**：

```plaintext
今天完成了 {任务列表}。

请帮我：
1. 更新 IMPLEMENTATION_PLAN.md 的任务状态
2. 在 CLAUDE.md 中记录今天遇到的问题和解决方案
3. 列出明天需要继续的工作
```