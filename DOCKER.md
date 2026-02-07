# Docker 启动指南

## 🐳 一键启动所有服务

使用 Docker Compose 可以一键启动 Qdrant 和 Neo4j 数据库服务。

### 快速启动

```bash
# 1. 启动 Docker 服务
./start-docker.sh

# 或者手动启动
docker compose up -d
```

### 服务地址

启动成功后，可以访问：

- **Qdrant API**: http://localhost:6333
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **Neo4j Browser**: http://localhost:7474
  - 用户名: `neo4j`
  - 密码: `password`

---

## 📋 完整启动流程

### 步骤 1: 启动 Docker 容器

```bash
# 启动所有数据库服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f
```

### 步骤 2: 准备 Python 环境

```bash
# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -e .
```

### 步骤 3: 初始化数据（首次运行）

```bash
# 初始化向量数据（Qdrant）
python scripts/init_seed_data.py

# 初始化图谱数据（Neo4j）
python scripts/init_graph.py
```

### 步骤 4: 启动后端 API

```bash
# 开发模式（自动重载）
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 或者使用项目脚本
python scripts/run_dev_server.py
```

### 步骤 5: 打开前端界面

在浏览器中打开：
```
frontend/index.html
```

或者启动本地服务器：
```bash
cd frontend
python3 -m http.server 8080
# 访问 http://localhost:8080
```

---

## 🧪 测试服务

### 测试数据库连接

```bash
# 测试 Qdrant
curl http://localhost:6333/health

# 测试 Neo4j
curl -u neo4j:password http://localhost:7474
```

### 测试后端 API

```bash
# 健康检查
curl http://localhost:8000/health

# 测试意图识别 + 检索
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "最近7天按用户的GMV总和同比",
    "top_k": 5
  }'
```

---

## 🛑 停止服务

```bash
# 停止所有容器
docker compose down

# 停止并删除数据卷（清空数据）
docker compose down -v

# 查看日志
docker compose logs qdrant
docker compose logs neo4j
```

---

## 🔧 常用命令

```bash
# 查看运行状态
docker compose ps

# 查看资源占用
docker stats

# 重启服务
docker compose restart

# 进入容器
docker exec -it chatbi-qdrant bash
docker exec -it chatbi-neo4j bash

# 备份数据
docker run --rm \
  -v chatbi_qdrant_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/qdrant_backup.tar.gz /data
```

---

## 📊 数据持久化

数据存储在 Docker 卷中：

```bash
# 查看所有卷
docker volume ls | grep chatbi

# 备份 Qdrant 数据
docker run --rm \
  -v chatbi_qdrant_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/qdrant_data_backup.tar.gz /data

# 备份 Neo4j 数据
docker run --rm \
  -v chatbi_neo4j_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/neo4j_data_backup.tar.gz /data
```

---

## ⚠️ 故障排查

### Qdrant 无法访问

```bash
# 检查容器状态
docker ps | grep qdrant

# 查看日志
docker compose logs qdrant

# 重启容器
docker compose restart qdrant
```

### Neo4j 无法访问

```bash
# 检查容器状态
docker ps | grep neo4j

# 查看日志
docker compose logs neo4j

# 重启容器
docker compose restart neo4j
```

### 端口冲突

如果端口被占用，修改 `docker-compose.yml` 中的端口映射：

```yaml
services:
  qdrant:
    ports:
      - "6334:6333"  # 改为其他端口
  neo4j:
    ports:
      - "7475:7474"  # 改为其他端口
      - "7688:7687"
```

同时更新 `.env` 文件中的配置。

---

## 🚀 性能优化

### Qdrant 性能调优

修改 `docker-compose.yml`：

```yaml
services:
  qdrant:
    environment:
      - QDRANT__STORAGE__OPTIMIZERS__INDEXING_THRESHOLD=20000
      - QDRANT__SERVICE__MAX_WORKERS=4
```

### Neo4j 性能调优

```yaml
services:
  neo4j:
    environment:
      - NEO4J_dbms_memory_heap_initial__size=1G
      - NEO4J_dbms_memory_heap_max__size=2G
      - NEO4J_dbms_memory_pagecache_size=1G
```

---

## 📝 更多信息

- [Qdrant 文档](https://qdrant.tech/documentation/)
- [Neo4j 文档](https://neo4j.com/docs/)
- [Docker Compose 文档](https://docs.docker.com/compose/)

---

**最后更新**: 2026-02-04
