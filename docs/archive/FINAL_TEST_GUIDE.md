# 真实数据集成 - 最终测试指南

## 🎯 问题已修复

**问题**: 前端调用错误的API路径
- ❌ 旧路径: `/api/debug/search-debug` (404错误)
- ✅ 新路径: `/debug/search-debug` (已修复)

---

## ✅ 系统状态验证

```bash
# 1. 后端服务正常
curl http://localhost:8000/health
# 预期: {"status":"healthy","service":"Semantic Query System"}

# 2. Debug API正常
curl -X POST http://localhost:8000/debug/search-debug \
  -H 'Content-Type: application/json' \
  -d '{"query":"GMV","top_k":3}'
# 预期: 返回包含7个execution_steps的JSON

# 3. 前端服务运行
ps aux | grep "python.*http.server.*8080"
# 预期: 显示运行中的进程

# 4. 前端文件已修复
grep "debug/search-debug" frontend/intent-visualization-v2.html
# 预期: 显示第671行的正确路径
```

---

## 🧪 完整测试步骤

### 步骤1: 清除浏览器缓存

**重要!** 测试前必须清除缓存,否则会看到旧版本:

**Chrome/Edge**:
- 按 `Cmd + Shift + Delete` (Mac) 或 `Ctrl + Shift + Delete` (Windows)
- 选择"缓存的图片和文件"
- 时间范围选"全部时间"
- 点击"清除数据"

**或者使用硬刷新**:
- Mac: `Cmd + Shift + R`
- Windows: `Ctrl + Shift + R`

### 步骤2: 访问意图分析界面

```
URL: http://localhost:8080/intent-visualization-v2.html
```

### 步骤3: 测试查询

在输入框中输入: `GMV上升趋势前10名`

点击 "🔍 检索" 按钮

### 步骤4: 观察流程动画

应该看到7个节点依次执行:
1. 💬 用户输入
2. 🎯 意图识别
3. 🔮 双路召回
4. 🧮 特征提取
5. ⚖️ 精排打分
6. ✅ 结果验证
7. 🎯 最终输出

### 步骤5: 点击节点查看详情

**重点测试 - 点击 "🎯 意图识别" 节点**:

右侧详情面板应显示:
- ✅ **执行时间**: 真实的毫秒数
- ✅ **状态**: ✅ 成功
- ✅ **输入数据**:
  - 原始查询: GMV上升趋势前10名
  - 会话ID: xxx
  - 会话轮次: 0
- ✅ **算法说明** (这是重点!):
  ```
  意图识别算法:
  1. 正则表达式匹配
     - 时间范围：(?P<数字>\d+)\s*(天|日|周|月|年)
     - 趋势分析：- (GMV|DAU|营收|销量|用户).{0,5}(上升|增长|提高)
     - 排序需求：(前|Top|top)\s*(\d+)
  ```
- ✅ **输出数据**:
  - core_query: GMV
  - trend_type: upward
  - sort_requirement: {"top_n": 10, "order": "desc"}

### 步骤6: 验证真实性

**确认以下内容都是真实的**:

1. ✅ **算法说明不是通用模板**,而是实际使用的正则表达式
2. ✅ **输出数据** (trend_type, sort_requirement) 是实际识别的结果
3. ✅ **执行时间** 是真实的,不是估算值
4. ✅ **输入数据** 包含真实的会话信息

---

## 🎉 成功标志

测试成功的标志:

### API层面
- [x] Debug API返回200 OK
- [x] 包含7个execution_steps
- [x] 每步包含input_data, algorithm, output_data, duration_ms, success

### 前端层面
- [x] 点击检索后显示流程动画
- [x] 7个节点依次完成
- [x] 点击任意节点显示详情面板
- [x] 详情面板显示真实数据

### 内容真实性
- [x] 意图识别算法包含实际正则表达式
- [x] 向量化算法显示实际模型名称和维度
- [x] 召回算法显示余弦相似度公式
- [x] 特征提取显示11维特征和权重
- [x] 精排算法显示加权求和公式
- [x] 所有输出都是实际执行结果

---

## 📱 快速测试页面

如果主界面有问题,可以使用独立的测试页面:

```bash
# 在浏览器中打开
open /tmp/test_debug_api.html

# 或在浏览器地址栏输入
file:///tmp/test_debug_api.html
```

这个页面会:
- 自动调用Debug API
- 显示完整的执行步骤
- 展示第1步的算法
- 展示第3步的输出

---

## 🐛 故障排除

### 问题1: 仍然显示"HTTP 404"

**原因**: 浏览器缓存

**解决**:
1. 按 `Cmd + Shift + R` (Mac) 或 `Ctrl + Shift + R` (Windows)
2. 或按 `Cmd + Option + R` (Mac) 强制刷新
3. 或清除浏览器缓存后重新加载

### 问题2: 后端返回422错误

**原因**: 请求体格式问题

**检查**: 后端日志应该显示具体错误

**解决**: 确保后端服务正在运行最新的代码

### 问题3: 前端显示"分析失败"

**检查**:
1. 打开浏览器开发者工具 (F12)
2. 切换到 Network 标签
3. 点击检索按钮
4. 查看 `search-debug` 请求的响应

**预期**: 状态码200,响应包含execution_steps

---

## 📋 验收清单

请逐项确认:

- [ ] 浏览器缓存已清除
- [ ] 访问 http://localhost:8080/intent-visualization-v2.html
- [ ] 输入 "GMV上升趋势前10名"
- [ ] 点击检索按钮
- [ ] 看到7步流程动画
- [ ] 点击 "🎯 意图识别" 节点
- [ ] 右侧显示详情面板
- [ ] 详情显示执行时间 (如: 0.95ms)
- [ ] 详情显示状态 (✅ 成功)
- [ ] 详情显示输入数据 (原始查询、会话ID等)
- [ ] 详情显示算法说明 (正则表达式、模式匹配等)
- [ ] 详情显示输出数据 (core_query, trend_type等)
- [ ] 算法说明包含实际提示词,不是通用模板
- [ ] 点击其他节点也能看到相应详情

---

## 🎯 用户需求确认

**用户原话**:
> "功能有了,但里面的内容,要与实际的符合。这样才能真正了解所有的解析链路。不是只要有个壳。包括如果涉及提示词,都可以将实际提示词体现出来。"

**验收标准**:
- ✅ 内容与实际符合 - 每步数据都来自真实执行
- ✅ 真正了解解析链路 - 7步完整透明展示
- ✅ 不是只有壳 - 输入/算法/输出都是真实数据
- ✅ 实际提示词体现出来 - 算法说明包含实际正则表达式和提示词

---

## 🚀 立即开始测试

```bash
# 1. 确认后端运行
curl http://localhost:8000/health

# 2. 打开浏览器 (已清除缓存)
open http://localhost:8080/intent-visualization-v2.html

# 3. 或使用测试页面
open /tmp/test_debug_api.html
```

**测试查询**:
- GMV上升趋势前10名
- DAU大于10000
- 最近30天GMV波动
- 它的增长率 (需要多轮对话)

---

**祝你测试成功!** 🎉
