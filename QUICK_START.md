# 🚀 智能问数系统 - 快速开始指南

## 系统概述

基于 **向量库 + 图谱 + GLM 摘要生成** 的混合语义检索系统，支持自然语言查询企业指标。

### 核心功能

- ✅ **智能检索**: 双路召回（向量 + 图谱）
- ✅ **GLM 摘要**: 自动生成多维度指标摘要
- ✅ **意图识别**: 理解查询意图和时间范围
- ✅ **API 管理**: 完整的指标管理 API
- ✅ **可视化界面**: 实时展示检索过程

---

## 📋 前置要求

### 必需服务

1. **Qdrant** (向量数据库)
   ```bash
   docker run -d -p 6333:6333 -p 6334:6334 \
     --name qdrant \
     qdrant/qdrant:v1.7.4
   ```

2. **Neo4j** (图数据库) - 可选
   ```bash
   docker run -d -p 7474:7474 -p 7687:7687 \
     --name neo4j \
     -e NEO4J_AUTH=neo4j/password \
     neo4j:5.15
   ```

3. **智谱 AI API Key** (GLM 摘要生成)
   - 访问: https://open.bigmodel.cn/usercenter/apikeys

---

## ⚙️ 配置

### 1. 环境变量配置

复制 `.env.example` 到 `.env` 并配置：

```bash
# 向量化器配置
VECTORIZER_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2

# 智谱 AI 配置
ZHIPUAI_API_KEY=your_actual_api_key_here
ZHIPUAI_MODEL=glm-4-flash
```

### 2. 安装依赖

```bash
pip install -e ".[dev]"
```

---

## 🚀 启动系统

### 使用启动脚本（推荐）

```bash
# 启动所有服务
./start-all-services.sh

# 停止所有服务
./stop-all-services.sh
```

### 手动启动

**后端:**
```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

**前端:**
```bash
cd frontend && python -m http.server 8080
```

---

## 📍 访问地址

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:8080 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |

---

## 🧪 快速测试

### 1. 健康检查

```bash
curl http://localhost:8000/health
```

### 2. 创建指标

```bash
curl -X POST http://localhost:8000/api/v1/management/metrics/single \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GMV",
    "code": "gmv",
    "description": "成交总额",
    "domain": "电商",
    "synonyms": ["成交金额"],
    "formula": "SUM(订单金额)",
    "importance": 0.95
  }'
```

### 3. 搜索指标

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query":"GMV是多少","top_k":5}'
```

---

## 📊 核心功能

### GLM 摘要生成

- **business_summary**: 业务含义说明
- **llm_friendly_text**: LLM 友好文本
- **rag_document**: RAG 文档格式

### 智能检索流程

```
用户查询 → 意图识别 → 双路召回 → 精排序 → 验证过滤 → 返回结果
```

---

## 🔧 常见问题

### Qdrant 连接失败

```bash
curl http://localhost:6333/
docker ps | grep qdrant
```

### 向量维度不匹配

```python
from src.config import settings
from qdrant_client import QdrantClient

client = QdrantClient(url=settings.qdrant.http_url)
client.delete_collection(settings.qdrant.collection_name)
# 重启服务自动创建
```

### GLM 摘要失败

```bash
# 检查 API Key
cat .env | grep ZHIPUAI_API_KEY
```

---

## 🎯 测试查询示例

- "GMV是多少"
- "最近 7 天的用户增长"
- "Top 10 地区的 DAU"
- "DAU 大于 10000 的地区"

---

**祝使用愉快！** 🎉
