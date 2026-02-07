# 智能问数系统 - 启动指南

## 🎯 两种启动方式

### 方式 1: 演示模式（推荐，立即可用）

**无需 Docker**，使用模拟数据，完整测试所有功能：

```bash
# 1. 启动后端服务
./run_demo.sh

# 或手动启动
export PYTHONPATH="/Users/wangzheng/Downloads/playDemo/AntigravityDemo/chatBI:$PYTHONPATH"
source .venv/bin/activate
python -m uvicorn scripts.run_demo_server:app --host 0.0.0.0 --port 8000
```

**访问地址：**
- API 服务: http://localhost:8000
- API 文档: http://localhost:8000/docs
- 前端界面: 在浏览器中打开 `frontend/index.html`

**功能测试：**
- ✅ 完整的意图识别（7维）
- ✅ 10 个模拟指标数据
- ✅ 智能匹配算法
- ✅ 前端可视化展示

---

### 方式 2: 完整模式（需要 Docker）

如果 Docker 网络问题已解决：

```bash
# 1. 启动数据库
docker compose up -d

# 2. 查看状态
docker compose ps

# 3. 初始化数据
source .venv/bin/activate
python scripts/init_seed_data.py
python scripts/init_graph.py

# 4. 启动后端
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🔧 Docker 问题修复

### 问题：无法拉取镜像

**原因：** 网络限制或代理配置

**解决方案 A: 配置代理**
```bash
# 打开 Docker Desktop
open /Applications/Docker.app

# Settings → Resources → Proxies
# 启用 Manual proxy configuration
# 填入代理服务器地址
```

**解决方案 B: 使用国内镜像源**

如果后续能访问，配置阿里云镜像：
```json
{
  "registry-mirrors": ["https://docker.mirrors.ustc.edu.cn"],
  "dns": ["8.8.8.8", "114.114.114.114"]
}
```

**解决方案 C: 手动下载镜像**

```bash
# 从其他设备导出镜像
docker save -o qdrant.tar qdrant/qdrant:v1.7.4
docker save -o neo4j.tar neo4j:5.15-community

# 在本机导入
docker load -i qdrant.tar
docker load -i neo4j.tar
```

---

## 🧪 快速测试

### 测试意图识别

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "最近7天按用户的GMV总和同比", "top_k": 5}'
```

### 测试查询示例

- `GMV` - 精确匹配
- `最近7天的活跃用户数` - 时间范围识别
- `本月营收总和` - 复合意图识别
- `按地区的转化率` - 维度识别
- `DAU同比` - 同比识别

---

## 📊 功能演示

演示模式支持完整的功能测试：

1. **意图识别**：时间、聚合、维度、比较类型
2. **智能匹配**：基于语义相似度
3. **前端可视化**：实时展示检索过程
4. **结果展示**：意图卡片 + 排序结果

**10 个内置指标：**
- GMV, DAU, MAU, ARPU, 转化率
- 客单价, LTV, 留存率, ROI, CTR

---

## 🎓 下一步

1. **启动演示服务器**：`./run_demo.sh`
2. **打开前端界面**：双击 `frontend/index.html`
3. **测试查询**：使用快速测试按钮或自定义查询
4. **查看意图识别结果**：观察意图卡片展示

**Docker 问题解决后**，可以切换到完整模式体验完整功能。

---

**当前推荐**：先使用演示模式测试功能，同时解决 Docker 网络问题。
