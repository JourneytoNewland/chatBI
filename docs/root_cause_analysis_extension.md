# 根因分析功能扩展方案

## 架构设计

### L4层：根因分析层（Root Cause Analysis Layer）

**位置**: 在 L3 LLM推理层之后，作为智能分析的增强层

**触发条件**:
- 查询包含"为什么"、"原因"、"怎么回事"等根因分析关键词
- L3层识别到异常趋势（下降/上升超过阈值）
- 用户明确请求分析

### 核心功能模块

```python
# src/inference/root_cause_analyzer.py

class RootCauseAnalyzer:
    """根因分析器"""

    def __init__(
        self,
        data_store: DataStore,  # 已有的MQL执行引擎
        llm_client: LLMClient,  # 已有的智谱AI客户端
    ):
        self.data_store = data_store
        self.llm_client = llm_client

    def analyze(
        self,
        query: str,
        intent: QueryIntent,
        execution_result: dict,
    ) -> RootCauseResult:
        """执行根因分析.

        Args:
            query: 用户查询
            intent: 已识别的意图
            execution_result: MQL执行结果

        Returns:
            RootCauseResult: 根因分析结果
        """
        # Step 1: 检测异常
        anomalies = self._detect_anomalies(execution_result)

        # Step 2: 多维分解
        dimensions = self._decompose_by_dimensions(
            intent.core_query,
            intent.dimensions or ["地区", "品类", "渠道"],
        )

        # Step 3: 趋势分析
        trends = self._analyze_trends(execution_result)

        # Step 4: 因果推断
        causal_factors = self._infer_causes(
            anomalies, dimensions, trends
        )

        # Step 5: 生成分析报告（LLM）
        report = self._generate_report(
            query, anomalies, dimensions, trends, causal_factors
        )

        return RootCauseResult(
            anomalies=anomalies,
            dimensions=dimensions,
            trends=trends,
            causal_factors=causal_factors,
            report=report,
        )
```

### 分析维度

#### 1. 时间维度分解
```python
def _decompose_by_time(self, metric: str, period: str):
    """按时间维度分解分析.

    示例查询:
    - SELECT date, value FROM metrics WHERE metric = 'GMV'
    - 计算同比、环比、移动平均
    - 识别趋势拐点
    """
    pass
```

#### 2. 维度下钻分析
```python
def _decompose_by_dimensions(self, metric: str, dimensions: list[str]):
    """按维度下钻分析.

    示例:
    - 按地区: 华东/华南/华北的贡献度
    - 按品类: 电子产品/服装/家居的表现
    - 按渠道: 线上/线下/分销的对比
    """
    pass
```

#### 3. 异常检测
```python
def _detect_anomalies(self, data: list) -> list[Anomaly]:
    """检测异常数据点.

    方法:
    - 统计方法: 3σ原则
    - 时间序列: 突变检测
    - 业务规则: 超过阈值
    """
    pass
```

#### 4. 因果推断
```python
def _infer_causes(
    self,
    anomalies: list[Anomaly],
    dimensions: dict,
    trends: dict,
) -> list[CausalFactor]:
    """推断因果关系.

    策略:
    - 规则引擎: IF 地区="华东" AND 下降>20% THEN 可能是供应链问题
    - LLM推理: 基于业务知识库推断
    - 关联分析: 检查相关指标的变化
    """
    pass
```

### API集成

```python
# src/api/complete_query.py

@app.post("/api/v3/query")
async def query(request: SearchRequest):
    # ... 现有代码 ...

    # 新增: 根因分析
    if _should_trigger_root_cause_analysis(request.query):
        root_cause_result = root_cause_analyzer.analyze(
            query=request.query,
            intent=final_intent,
            execution_result={"data": data, "sql": sql},
        )

        response.root_cause_analysis = {
            "anomalies": root_cause_result.anomalies,
            "dimension_breakdown": root_cause_result.dimensions,
            "trend_analysis": root_cause_result.trends,
            "causal_factors": root_cause_result.causal_factors,
            "report": root_cause_result.report,
        }

    return response
```

### 前端展示

```javascript
// frontend/index.html

function displayRootCauseModule(data) {
    const rootCause = data.root_cause_analysis;

    let html = `
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; border-radius: 12px; padding: 24px; margin-bottom: 20px;">
            <div style="font-size: 14px; opacity: 0.9; margin-bottom: 8px;">
                🔍 根因分析
            </div>
            <div style="font-size: 24px; font-weight: 700;">
                ${rootCause.report.summary}
            </div>
        </div>

        <!-- 异常检测 -->
        <div class="section">
            <h3>⚠️ 检测到的异常</h3>
            ${rootCause.anomalies.map(anomaly => `
                <div class="anomaly-card">
                    <div style="color: ${anomaly.severity === 'high' ? '#f56565' : '#ed8936'}">
                        ${anomaly.description}
                    </div>
                    <div>时间: ${anomaly.timestamp}</div>
                    <div>偏离度: ${(anomaly.deviation * 100).toFixed(1)}%</div>
                </div>
            `).join('')}
        </div>

        <!-- 维度下钻 -->
        <div class="section">
            <h3>📊 维度分解</h3>
            ${rootCause.dimension_breakdown.map(dim => `
                <div class="dimension-card">
                    <h4>${dim.name}</h4>
                    <div class="chart">
                        ${renderBarChart(dim.values)}
                    </div>
                    <div class="insight">
                        主要影响: ${dim.top_contributor}
                    </div>
                </div>
            `).join('')}
        </div>

        <!-- 因果推断 -->
        <div class="section">
            <h3>🔗 可能原因</h3>
            <ul>
                ${rootCause.causal_factors.map(factor => `
                    <li>
                        <strong>${factor.name}</strong>
                        <div>置信度: ${(factor.confidence * 100).toFixed(0)}%</div>
                        <div>${factor.explanation}</div>
                    </li>
                `).join('')}
            </ul>
        </div>
    `;

    document.getElementById('root-cause-content').innerHTML = html;
}
```

## 实施步骤（预计2-3天）

### Day 1: 核心分析逻辑
- [ ] 实现 RootCauseAnalyzer 基础框架
- [ ] 实现异常检测（统计方法）
- [ ] 实现维度下钻分析
- [ ] 编写单元测试

### Day 2: 因果推断与LLM集成
- [ ] 实现规则引擎（基于业务规则）
- [ ] 实现LLM因果推理
- [ ] 实现报告生成
- [ ] 集成到API

### Day 3: 前端展示与优化
- [ ] 实现前端展示组件
- [ ] 添加可视化图表
- [ ] 优化交互体验
- [ ] 端到端测试

## 优势分析

### 1. 架构优势
- ✅ **非侵入式**: 不破坏现有架构
- ✅ **可插拔**: 独立模块，易于维护
- ✅ **可扩展**: 可以添加更多分析维度

### 2. 数据复用
- ✅ **MQL引擎**: 已有的数据执行能力
- ✅ **意图识别**: 已有的三层意图识别
- ✅ **召回系统**: 已有的指标发现能力
- ✅ **LLM集成**: 已有的智谱AI接口

### 3. 快速迭代
- ✅ **独立测试**: 根因分析模块可以独立测试
- ✅ **渐进增强**: 先实现基础功能，再逐步增强
- ✅ **A/B测试**: 可以与基线对比效果

## 示例场景

### 场景1: GMV下降分析
```
用户查询: "为什么最近7天GMV下降了15%？"

L4分析流程:
1. 异常检测: 识别到第5天GMV突然下降20%
2. 时间分解: 工作日正常，周末异常
3. 维度下钻:
   - 按地区: 华东地区下降40%（主因）
   - 按品类: 电子产品无库存
4. 因果推断:
   - 供应链问题（置信度85%）
   - 竞品促销（置信度60%）
   - 季节性波动（置信度40%）

LLM生成报告:
"GMV在最近7天下降了15%，主要原因是华东地区供应链
问题导致电子产品缺货。建议优先解决库存问题。"
```

### 场景2: DAU异常增长
```
用户查询: "为什么DAU突然增长了50%？"

L4分析流程:
1. 异常检测: 识别到DAU在3天内从10万涨到15万
2. 渠道分析: 新增渠道贡献了80%的增长
3. 用户画像: 新用户以年轻用户为主
4. 因果推断:
   - 新渠道推广（置信度95%）
   - 病毒式传播（置信度70%）

LLM生成报告:
"DAU增长主要由新渠道推广驱动，建议加大该渠道投入，
同时关注用户留存率。"
```

## 总结

**扩展难度**: ⭐⭐ (简单)
**开发时间**: 2-3天
**依赖模块**: 全部已有
**新增代码**: 约500行（Python: 300行, JS: 200行）

**关键优势**:
- 架构清晰，模块独立
- 复用现有能力，无需重复造轮
- 渐进增强，风险可控
- 效果可衡量，易于优化

这就是为什么当前架构可以快速扩展根因分析功能！
