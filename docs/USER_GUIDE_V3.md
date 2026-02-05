# 智能问数系统 v3.0 - 使用指南

## 🚀 服务状态

### 前端服务
- **地址**: http://localhost:8080
- **状态**: ✅ 运行中
- **页面**:
  - index_v3.html (全链路可视化，包含MQL→SQL→数据→解读)
  - index.html (原始版本)

### 后端API服务
- **地址**: http://localhost:8000
- **状态**: ⏳ 正在加载模型（BGE-M3，约30-60秒）
- **API文档**: http://localhost:8000/docs (启动后访问)

## 📋 完整的执行链路

### 1. 意图识别（Intent Recognition）
**输入**: 自然语言查询
**输出**: 结构化意图对象
```json
{
  "core_query": "GMV",
  "time_range": {"start": "2024-01-01", "end": "2024-01-07"},
  "aggregation_type": "SUM",
  "dimensions": [],
  "comparison_type": null
}
```

### 2. MQL生成（MQL Generation）
**输入**: 意图对象
**输出**: MQL查询字符串
```
GMV[SUM](2024-01-01 TO 2024-01-07)
```

### 3. SQL生成（SQL Generation）
**输入**: MQL查询
**输出**: SQL查询语句
```sql
SELECT SUM(f.order_amount) AS value
FROM fact_orders f
JOIN dim_date d ON f.date_id = d.date_id
WHERE f.date_id BETWEEN %(start_date)s AND %(end_date)s
```

### 4. 数据执行（Query Execution）
**输入**: SQL查询
**输出**: 查询结果数据
```json
[
  {"date": "2024-01-01", "value": 523456.78, "metric": "GMV", "unit": "元"},
  {"date": "2024-01-02", "value": 545678.90, "metric": "GMV", "unit": "元"}
]
```

### 5. LLM提示词构建（LLM Prompt）
**输入**: 查询 + 数据分析结果
**输出**: 结构化提示词
```
你是一个专业的数据分析助手。请基于以下查询结果生成智能解读：

## 用户查询
最近7天GMV总和

## 指标信息
- 指标名称：GMV
- 指标定义：商品交易总额
- 单位：元

## 数据分析结果
- 趋势：上升 ↗
- 变化率：15.2%
- 波动性：8.5%
- 最小值：480000
- 最大值：650000
- 平均值：565000

## 查询结果（前5条）
1. 2024-01-01: 520000
2. 2024-01-02: 535000
3. 2024-01-03: 550000
4. 2024-01-04: 565000
5. 2024-01-05: 580000

请生成：
1. **summary**（总结，2-3句话）
2. **key_findings**（关键发现，3-5点）
3. **insights**（深入洞察，2-3点）
4. **suggestions**（行动建议，2-3点）
```

### 6. 智能解读生成（LLM Interpretation）
**输入**: LLM提示词
**输出**: 结构化解读
```json
{
  "summary": "GMV呈显著上升趋势，7天内增长15.2%，平均每天增长2.2%。",
  "trend": "upward",
  "key_findings": [
    "GMV从52万增长到65万，增长15.2%",
    "平均每天增长2.2%，增速稳定",
    "最低值48万，最高值65万"
  ],
  "insights": [
    "增长趋势可能受促销活动影响",
    "华东地区贡献最大，占比40%"
  ],
  "suggestions": [
    "继续当前营销策略",
    "关注华东地区客户需求变化"
  ],
  "confidence": 0.82
}
```

## 🎨 前端页面特性

### index_v3.html（全链路可视化）
- ✅ 意图识别结果展示
- ✅ MQL查询展示
- ✅ SQL查询展示（语法高亮）
- ✅ 数据可视化（折线图 + 表格）
- ✅ LLM提示词完整展示
- ✅ 智能解读结果：
  - 趋势标识（上升/下降/波动/稳定）
  - 关键指标（变化率、波动性、最值）
  - 总结
  - 关键发现
  - 深入洞察
  - 行动建议
  - 置信度

## 🧪 测试查询示例

### 基础查询
```
最近7天GMV总和
最近30天订单量
本月DAU平均值
```

### 聚合查询
```
最近7天GMV的平均值
最近30天支付订单总数
```

### 分组查询
```
最近7天按地区统计GMV
最近30天按渠道统计DAU
```

### 过滤查询
```
最近7天华东地区的GMV
最近30天APP渠道的订单量
```

## 🔧 故障排查

### API服务未启动
```bash
# 检查服务状态
ps aux | grep uvicorn

# 查看日志
tail -f /tmp/api_server.log

# 重启服务
pkill -f uvicorn
python -m uvicorn src.api.v2_query_api:app --host 0.0.0.0 --port 8000
```

### 前端无法连接API
1. 确认API服务已启动：http://localhost:8000/docs
2. 检查CORS设置（已配置允许所有来源）
3. 检查浏览器控制台错误信息

### 模型加载慢
- BGE-M3模型首次加载需要30-60秒
- 后续查询会很快（<500ms）

### 智能解读失败
- 检查ZhipuAI API Key配置
- 查看日志中的错误信息
- 系统会自动降级到模板解读

## 📊 性能指标

- 意图识别: <1s
- MQL生成: <100ms
- SQL生成: <100ms
- 数据查询: <500ms
- 智能解读: <3s（LLM调用）
- **总响应时间**: 约3-5秒

## 📝 代码结构

```
src/
├── api/
│   └── v2_query_api.py          # API接口（包含智能解读）
├── database/
│   └── postgres_client.py        # PostgreSQL客户端
├── inference/
│   └── enhanced_hybrid.py       # 意图识别
├── mql/
│   ├── engine.py                 # MQL执行引擎
│   ├── sql_generator.py          # SQL生成器
│   ├── intelligent_interpreter.py # 智能解读器
│   └── models.py                 # 数据模型
```

## 🎯 下一步优化

1. **前端优化**
   - 添加加载进度条
   - 优化图表交互
   - 添加导出功能

2. **性能优化**
   - 实现查询缓存
   - 批量查询支持
   - 流式响应

3. **功能扩展**
   - 支持同比/环比分析
   - 多维度交叉分析
   - 自定义Dashboard

---

**成为真正的智能问数智能体！** 🚀
