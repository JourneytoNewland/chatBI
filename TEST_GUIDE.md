# 完整测试指南

## 🎯 测试目标

验证真实的执行链路数据已正确集成到前端可视化界面。

---

## ✅ 前置条件检查

### 1. 后端服务
```bash
curl http://localhost:8000/health
```
**预期输出**: `{"status":"healthy","service":"Semantic Query System"}`

### 2. Debug API
```bash
curl -X POST http://localhost:8000/debug/search-debug \
  -H 'Content-Type: application/json' \
  -d '{"query":"GMV","top_k":3}'
```
**预期输出**: 包含7个execution_steps的JSON

### 3. 前端服务
```bash
curl http://localhost:8080
```
**预期输出**: HTML内容或文件列表

---

## 🧪 测试步骤

### 方式1: 使用独立测试页面

1. **打开测试页面**
   ```bash
   open /tmp/test_debug_api.html
   ```
   或在浏览器地址栏输入: `file:///tmp/test_debug_api.html`

2. **观察结果**
   - ✅ API调用成功
   - ✅ 7个执行步骤全部显示
   - ✅ 第1步的意图识别算法完整展示
   - ✅ 第3步的向量召回输出真实数据

### 方式2: 使用真实前端界面

1. **访问意图分析界面**
   - URL: http://localhost:8080/intent-visualization-v2.html
   - 或通过统一平台: http://localhost:8080/dashboard.html

2. **输入查询**
   ```
   GMV上升趋势前10名
   ```

3. **点击 "🔍 检索" 按钮**
   - 观察7步流程动画执行
   - 每个节点显示执行时间
   - 第一个节点自动高亮并显示详情

4. **点击每个节点查看详情**
   - 💬 用户输入 - 显示原始查询
   - 🎯 意图识别 - **重点查看**:显示完整的正则表达式和模式匹配
   - 🔮 双路召回 - 显示向量召回+图谱召回
   - 🧮 特征提取 - 显示11维特征和权重
   - ⚖️ 精排打分 - 显示评分公式和排名
   - ✅ 结果验证 - 显示验证规则和结果
   - 🎯 最终输出 - 显示最终候选列表

5. **验证内容真实性**
   - 意图识别的算法说明中包含实际的正则表达式
   - 向量召回的算法说明中包含余弦相似度公式
   - 精排打分的算法说明中包含加权求和公式
   - 所有数据都是真实执行的结果,不是mock

### 方式3: 命令行测试

```bash
# 测试Debug API并格式化输出
curl -s -X POST http://localhost:8000/debug/search-debug \
  -H 'Content-Type: application/json' \
  -d '{"query":"GMV上升趋势前10名","top_k":3}' \
  | python3 -m json.tool \
  | head -200
```

---

## 📊 预期结果

### Debug API 响应结构

```json
{
  "query": "GMV上升趋势前10名",
  "total_duration_ms": 733.00,
  "execution_steps": [
    {
      "step_name": "意图识别",
      "step_type": "intent_recognition",
      "duration_ms": 0.95,
      "success": true,
      "input_data": {
        "原始查询": "GMV上升趋势前10名",
        "会话ID": "1770275921"
      },
      "algorithm": "意图识别算法：\n1. 正则表达式匹配\n   ...",
      "algorithm_params": {
        "模型": "规则引擎 + 正则表达式"
      },
      "output_data": {
        "core_query": "GMV",
        "trend_type": "upward",
        "sort_requirement": {"top_n": 10}
      }
    },
    // ... 其他6个步骤
  ]
}
```

### 前端展示效果

**详情面板应显示**:
1. **执行时间**: 真实的毫秒数
2. **状态**: ✅ 成功 或 ❌ 失败
3. **输入数据**: 格式化的真实输入
4. **算法说明**: 包含提示词、公式、正则表达式
5. **输出数据**: 格式化的真实输出

---

## 🔍 关键验证点

### 1. 算法真实性

**意图识别算法应包含**:
```
意图识别算法：
1. 正则表达式匹配
   - 时间范围：(?P<数字>\d+)\s*(天|日|周|月|年)
   - 趋势分析：- (GMV|DAU|营收|销量|用户).{0,5}(上升|增长|提高)
   - 排序需求：(前|Top|top)\s*(\d+)
   - 阈值过滤：(\S+?)\s*(>|<|>=|<=)\s*(\d+)
```

### 2. 数据真实性

**向量召回输出应包含**:
- `召回数量`: 实际的数字
- `top候选`: 真实的候选指标列表
- 每个候选包含: name, score, payload

### 3. 时间真实性

**执行时间应该是**:
- 意图识别: < 10ms
- 向量化: ~700ms (首次加载模型)
- 向量召回: ~20-50ms
- 特征提取: < 1ms
- 精排打分: < 1ms
- 结果验证: < 1ms

---

## ❌ 常见问题排查

### 问题1: "HTTP 404: Not Found"

**原因**: API路径错误

**检查**:
```bash
# 查看后端可用路由
curl http://localhost:8000/openapi.json | grep -o '"/[^"]*"' | sort
```

**修复**: 确保前端调用 `/debug/search-debug` 而不是 `/api/debug/search-debug`

### 问题2: 前端显示"分析失败"

**检查**:
1. 后端服务是否运行: `curl http://localhost:8000/health`
2. Debug API是否可用: `curl -X POST http://localhost:8000/debug/search-debug ...`
3. 浏览器控制台是否有CORS错误

### 问题3: 数据显示不完整

**检查**:
1. 打开浏览器开发者工具 (F12)
2. 查看Network标签中的API响应
3. 确认响应包含完整的execution_steps数组

---

## ✅ 测试清单

- [ ] 后端服务正常运行
- [ ] Debug API返回7个步骤
- [ ] 每步包含input_data
- [ ] 每步包含algorithm (算法说明)
- [ ] 每步包含output_data
- [ ] 每步包含duration_ms
- [ ] 前端可以访问
- [ ] 输入查询后显示流程动画
- [ ] 点击节点显示真实详情
- [ ] 算法说明包含提示词/公式
- [ ] 输入数据格式正确
- [ ] 输出数据格式正确

---

## 🎉 成功标志

测试成功的标志:
1. ✅ 所有7个步骤执行成功
2. ✅ 每个步骤显示真实的输入数据
3. ✅ 每个步骤显示完整的算法说明(包含提示词)
4. ✅ 每个步骤显示实际的输出数据
5. ✅ 执行时间精确且合理
6. ✅ 前端界面正确展示所有信息

---

## 📝 测试报告模板

```markdown
## 测试报告 - [日期]

### 测试环境
- 后端: http://localhost:8000
- 前端: http://localhost:8080
- 测试查询: "GMV上升趋势前10名"

### 测试结果
- ✅ 后端服务: 正常
- ✅ Debug API: 正常 (7个步骤)
- ✅ 前端界面: 正常
- ✅ 真实数据: 是

### 详细步骤
1. 意图识别: 0.95ms ✅
   - 算法: 包含完整正则表达式
2. 查询向量化: 688.14ms ✅
   - 算法: 显示模型和向量维度
3. 向量召回: 43.04ms ✅
   - 输出: 4个候选
4. 图谱召回: 0.00ms ✅
5. 特征提取: 0.19ms ✅
   - 算法: 11维特征
6. 精排打分: 0.24ms ✅
   - 输出: 3个排名结果
7. 结果验证: 0.19ms ✅
   - 输出: 3个通过, 0个拒绝

### 结论
✅ 真实数据集成成功,所有功能正常!
```
