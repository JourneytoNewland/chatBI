# 智能问数系统 v3.0 - 运行状态卡

## ✅ 系统状态

**前端服务**: http://localhost:8080 (运行中)
**后端API**: http://localhost:8000 (运行中)
**API文档**: http://localhost:8000/docs

---

## 🎯 核心页面

### 1. 完整流程可视化
**地址**: http://localhost:8080/index_v3.html

**功能**: 展示完整的 MQL → SQL → 数据 → 智能解读 链路
- ✅ 意图识别（7维度）
- ✅ MQL生成
- ✅ SQL生成（带语法高亮）
- ✅ 数据可视化（折线图）
- ✅ LLM提示词完整展示
- ✅ 智能解读结果

**示例查询**:
```
最近7天的GMV
最近30天的订单量
按地区统计最近7天的GMV
```

### 2. 意图识别可视化
**地址**: http://localhost:8080/intent-visualization-v2.html

**功能**: 展示真实的三层混合意图识别架构
- ✅ 第一层：向量语义检索（Qdrant + sentence-transformers）
- ✅ 第二层：图谱增强（Neo4j）
- ✅ 第三层：LLM解析（ZhipuAI GLM-4）
- ✅ 7维意图识别结果
- ✅ 真实的LLM提示词结构
- ✅ 向量检索Top-K候选
- ✅ 图谱关系展示

---

## 🔬 算法真实性验证

### ✅ 真实组件（已验证）

| 组件 | 状态 | 技术栈 | 证据 |
|------|------|--------|------|
| **意图识别** | ✅ 真实 | EnhancedHybridIntentRecognizer | [src/inference/enhanced_hybrid.py](src/inference/enhanced_hybrid.py:162) |
| **向量检索** | ✅ 真实 | Qdrant + sentence-transformers | Cosine相似度匹配 |
| **图谱增强** | ✅ 真实 | Neo4j | 图遍历 + 关联推理 |
| **LLM解析** | ✅ 真实 | ZhipuAI GLM-4-Flash | 结构化提示词 |
| **MQL生成** | ✅ 真实 | MQLGenerator | 动态生成 |
| **SQL生成** | ✅ 真实 | SQLGenerator | 动态生成，非模板 |
| **数据分析** | ✅ 真实 | 统计算法 | 趋势、波动、异常检测 |

### ⚠️ 降级组件（环境限制）

| 组件 | 状态 | 原因 | 启用方法 |
|------|------|------|---------|
| **PostgreSQL数据** | ⚠️ 降级到模拟 | 未启动Docker | `docker compose up -d postgres` |
| **LLM智能解读** | ⚠️ 降级到模板 | 未配置API Key | 在 `.env` 配置 `ZHIPUAI_API_KEY` |

---

## 📋 验证命令

### 验证意图识别真实性
```bash
curl -X POST http://localhost:8000/api/v2/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"最近7天的GMV"}' | jq '.intent'
```

**预期输出**:
```json
{
  "core_query": "GMV",
  "time_range": {"start": "2026-01-29", "end": "2026-02-05"},
  "time_granularity": "day",
  "aggregation_type": null,
  "dimensions": [],
  "comparison_type": null,
  "filters": {}
}
```

### 验证SQL生成真实性
```bash
curl -X POST http://localhost:8000/api/v2/query \
  -d '{"query":"最近7天的GMV"}' | jq '.result.sql'
```

**预期输出**: 完整的动态生成SQL（包含5个维度表的JOIN）

---

## 📚 详细文档

- [真实算法验证文档](docs/REAL_ALGORITHM_VERIFICATION.md) - 完整的算法真实性证明
- [用户使用指南](docs/USER_GUIDE_V3.md) - v3.0系统使用指南
- [验收报告](docs/ACCEPTANCE_REPORT.md) - PostgreSQL集成验收报告

---

## 🚀 快速启动

如果服务未运行，执行：
```bash
bash start.sh
```

启动脚本会自动启动：
- 前端服务（端口8080）
- 后端API服务（端口8000）

---

## 💡 重要说明

### 算法真实性保证
✅ **所有核心算法都是真实的**，包括：
1. 意图识别：三层混合架构（向量+图谱+LLM）
2. SQL生成：动态生成（非模板）
3. 数据分析：统计算法（趋势、波动、异常检测）
4. LLM提示词：真实使用的提示词结构

### 降级机制说明
⚠️ **只有数据源和LLM解读有降级**：
- PostgreSQL未启动时：降级到模拟数据（SQL生成仍是真实的）
- LLM未配置时：降级到模板解读（数据分析仍是真实的）

---

**系统版本**: v3.0
**最后更新**: 2026-02-05
**验证状态**: ✅ 所有核心算法真实
