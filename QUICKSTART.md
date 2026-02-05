# 🎉 智能问数系统 - 快速使用指南

## ✅ 服务状态

### 前端服务
- **地址**: http://localhost:8080
- **页面**: http://localhost:8080/index_v3.html
- **状态**: ✅ 运行中

### 后端API服务
- **地址**: http://localhost:8000
- **状态**: ✅ 运行中
- **API文档**: http://localhost:8000/docs

---

## 🚀 快速开始

### 方式1: 使用前端页面（推荐）

1. **打开浏览器访问**:
   http://localhost:8080/index_v3.html

2. **输入查询**（推荐示例）:
   - `最近7天的GMV`
   - `最近30天的订单量`
   - `本周的DAU`
   - `按地区统计GMV`

3. **点击"查询"按钮**

4. **查看完整的执行链路**:
   - 步骤1: 意图识别（7个维度）
   - 步骤2: MQL生成
   - 步骤3: SQL生成（带语法高亮）
   - 步骤4: 数据可视化（折线图+表格）
   - 步骤5: LLM提示词
   - 步骤6: 智能解读（趋势、发现、洞察、建议）

---

### 方式2: 使用curl命令

```bash
# 查询最近7天的GMV
curl -X POST http://localhost:8000/api/v2/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"最近7天的GMV"}'
```

---

## 📊 完整的执行链路示例

**查询**: "最近7天的GMV"

### 响应结构
```json
{
  "query": "最近7天的GMV",

  "intent": {
    "core_query": "GMV",
    "time_range": {
      "start": "2026-01-29",
      "end": "2026-02-05"
    },
    "time_granularity": "day",
    "aggregation_type": null
  },

  "mql": "SELECT GMV\nFROM 2026-01-29 TO 2026-02-05\nLIMIT 10",

  "result": {
    "sql": "SELECT f.date_id AS date, order_amount AS value\nFROM fact_orders f\nJOIN dim_date d ON f.date_id = d.date_id\nWHERE f.date_id BETWEEN %(start_date)s AND %(end_date)s",

    "metric": {
      "metric_id": "gmv",
      "name": "GMV",
      "description": "成交总额，一定时期内成交商品的总金额",
      "unit": "元",
      "formula": "SUM(order_amount)"
    },

    "result": [
      {
        "date": "2026-01-29",
        "value": 543081.28,
        "metric": "GMV",
        "unit": "元"
      }
    ]
  },

  "interpretation": {
    "summary": "GMV呈上升趋势，7天内增长XX%",
    "trend": "upward",
    "key_findings": [...],
    "insights": [...],
    "suggestions": [...],
    "confidence": 0.82
  }
}
```

---

## 🎯 支持的查询类型

### 基础查询
- `最近7天的GMV` ✅
- `最近30天的订单量`
- `本月DAU`

### 聚合查询
- `GMV的总和`
- `订单数量的平均值`

### 分组查询
- `按地区统计GMV`
- `按品类统计订单量`

### 时间范围查询
- `最近7天`
- `本月`
- `上季度`
- `2024年1月`

---

## 🔍 故障排查

### 问题1: 前端显示 "Failed to fetch"

**原因**: 后端API服务未启动

**解决方法**:
```bash
# 检查API服务状态
lsof -i :8000 | grep LISTEN

# 如果没有输出，重新启动
python -m src.api.v2_query_api > /tmp/api_server.log 2>&1 &
```

### 问题2: 查询返回 "指标不存在"

**原因**: 查询格式不正确

**解决方法**:
- ✅ 正确: `最近7天的GMV`
- ❌ 错误: `最近7天GMV总和`（会被识别为"GMV总和"这个指标，但实际指标是"GMV"）

### 问题3: 查询很慢

**原因**: 模型首次加载需要时间

**解决方法**:
- 首次查询需要30-60秒加载模型
- 后续查询会很快（<500ms）

---

## 📝 查看日志

```bash
# 查看API日志
tail -f /tmp/api_server.log

# 查看前端日志
tail -f /tmp/frontend.log
```

---

## 🛑 停止服务

```bash
# 停止所有服务
pkill -f 'http.server'  # 停止前端
pkill -f 'v2_query_api'  # 停止后端
```

---

## 📚 更多信息

- **API文档**: http://localhost:8000/docs
- **使用指南**: `docs/USER_GUIDE_V3.md`
- **部署指南**: `docs/POSTGRESQL_INTEGRATION.md`

---

**成为真正的智能问数智能体！** 🚀
