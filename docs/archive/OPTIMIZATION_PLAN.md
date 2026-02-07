# 智能问数系统优化方案 - 最优版本

## 🎯 目标
创建一个**真实、泛化、智能**的系统，每一步都使用最优算法，展示形式为流程引擎节点。

## 📋 当前问题诊断

### 问题1：意图识别不够泛化
- ✅ "最近7天的GMV" → 正确识别core_query="GMV"
- ❌ "本月按渠道统计DAU" → 错误识别为core_query="按渠道统计DAU"
- ❌ "2024年1月的订单转化率" → 可能错误

**根本原因**：
- LLM识别时没有传递候选指标列表
- Few-Shot示例缺少"按维度统计"模式
- 维度提取规则不够明确

### 问题2：前端展示不够直观
- 当前：简单的卡片展示
- 期望：流程引擎节点形式，清晰展示每一步的输入输出

## 🔧 解决方案

### Step 1: 修复意图识别泛化能力 ✅ 已完成

**文件修改**：
1. `src/inference/zhipu_intent.py` - _build_prompt()方法
   - 添加candidates参数
   - 在提示词中包含可用指标列表
   - 添加明确的"按XX统计"模式识别规则

2. `src/inference/zhipu_intent.py` - recognize()方法
   - 添加candidates参数

3. `src/inference/enhanced_hybrid.py` - _layer3_llm_inference()
   - 添加candidates参数
   - 传递给LLM recognizer

4. `src/inference/enhanced_hybrid.py` - recognize()
   - 传递L2的candidates给L3

**关键改进**：
```python
# 修改后的提示词规则
2. **维度提取**：
   - "按XX统计"、"按XX分析"、"按XX看" → dimensions包含"XX"
   - 例如："按渠道统计DAU" → dimensions=["渠道"], core_query="DAU"

3. **聚合词识别**：
   - "总和"、"总计" → aggregation_type="sum"
   - "平均"、"均值" → aggregation_type="avg"
   - "统计"（无聚合词） → aggregation_type=null
```

### Step 2: 优化前端展示为流程引擎形式

**新页面**: `frontend/intent-flow.html`

**展示形式**：
```
[用户输入] → [L1:规则匹配] → [L2:语义检索] → [L3:LLM解析] → [最终意图]
    ↓            ↓              ↓              ↓              ↓
  失败        Top-5候选      Top-1候选      7维结果       core_query
```

每个节点显示：
- ✅/❌ 状态
- 输入数据
- 输出结果
- 耗时
- 置信度

### Step 3: 完整测试验证

**测试用例**：
1. 最近7天的GMV（基础查询）
2. 本月按渠道统计DAU（维度+时间）
3. 2024年1月的订单转化率（精确时间+复杂指标）
4. 按地区统计GMV同比（维度+对比）
5. 本周ARPU和AOE（多指标）

## 📁 关键文件

### 已修改文件
- `src/inference/zhipu_intent.py` - LLM提示词优化
- `src/inference/enhanced_hybrid.py` - 候选指标传递

### 待创建文件
- `frontend/intent-flow.html` - 流程引擎可视化页面
- `frontend/intent-viz-final.html` - 优化版意图可视化页面

## ✅ 验收标准

1. **功能验收**
   - [ ] 所有3个测试用例通过
   - [ ] 意图识别准确率 ≥ 90%
   - [ ] 流程引擎页面展示清晰

2. **质量验收**
   - [ ] 真实算法（非硬编码）
   - [ ] 泛化能力（支持各种查询模式）
   - [ ] 可视化直观（流程节点形式）

## 🚀 实施步骤

### 步骤1：重启API服务（使代码生效）
```bash
pkill -f "uvicorn.*v2_query_api"
python -m uvicorn src.api.v2_query_api:app --host 0.0.0.0 --port 8000
```

### 步骤2：测试所有用例
```bash
# 用例1
curl -X POST http://localhost:8000/api/v2/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"最近7天的GMV"}'

# 用例2
curl -X POST http://localhost:8000/api/v2/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"本月按渠道统计DAU"}'

# 用例3
curl -X POST http://localhost:8000/api/v2/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"2024年1月的订单转化率"}'
```

### 步骤3：创建流程引擎可视化页面
包含：
- 三层架构流程图
- 每层的详细结果
- 实时执行动画

### 步骤4：完整测试（至少2次）
- 第一次：功能测试
- 第二次：稳定性测试

## 📊 预期结果

**修复后的意图识别**：
- "本月按渠道统计DAU" →
  - core_query: "DAU"
  - dimensions: ["渠道"]
  - time_range: 本月
  - aggregation_type: null

- "2024年1月的订单转化率" →
  - core_query: "conversion_rate"
  - time_range: 2024年1月
  - time_granularity: "month"
