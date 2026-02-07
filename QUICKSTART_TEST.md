# 快速测试指南

## 🚀 快速验证项目

### 方式1: 演示模式（最简单）

```bash
# 1. 启动演示服务器
bash scripts/run_demo.sh

# 2. 在浏览器打开
open http://localhost:8080
# 或手动打开 frontend/index.html
```

**演示模式特点**:
- ✅ 无需数据库
- ✅ 无需Docker
- ✅ 包含模拟数据
- ✅ 快速启动（<5秒）

### 方式2: 完整模式（需要数据库）

```bash
# 1. 启动PostgreSQL（可选）
docker compose up -d postgres
# 初始化数据库
bash scripts/init-postgres.sh

# 2. 启动完整API服务
python -m uvicorn src.api.main:app --host localhost --port 8000

# 3. 测试API
curl -X POST http://localhost:8000/api/v3/query \
  -H "Content-Type: application/json" \
  -d '{"query": "最近7天GMV"}'

# 4. 查看API文档
open http://localhost:8000/docs
```

## 🧪 快速测试脚本

### 测试API健康

```bash
# 测试健康检查
curl http://localhost:8000/health

# 预期输出:
# {"status":"healthy","service":"Semantic Query System"}
```

### 测试v3查询API

```bash
# 简单查询
curl -X POST http://localhost:8000/api/v3/query \
  -H "Content-Type: application/json" \
  -d '{"query": "GMV"}'

# 时间范围查询
curl -X POST http://localhost:8000/api/v3/query \
  -H "Content-Type: application/json" \
  -d '{"query": "最近7天GMV"}'

# 维度分组查询
curl -X POST http://localhost:8000/api/v3/query \
  -H "Content-Type: application/json" \
  -d '{"query": "按地区统计DAU"}'
```

## 📊 验证功能

### 1. 验证路由注册

```bash
python3 -c "
from src.api.main import app
v3_routes = [r.path for r in app.routes if hasattr(r, 'path') and '/api/v3' in r.path]
print('v3路由:', v3_routes)
"
# 预期输出: v3路由: ['/api/v3/query']
```

### 2. 验证模块导入

```bash
python3 -c "
from src.inference.enhanced_hybrid import EnhancedHybridIntentRecognizer
from src.mql.engine_v2 import MQLExecutionEngineV2
from src.database.postgres_client import postgres_client

print('✅ 所有核心模块导入成功')
"
```

### 3. 验证配置

```bash
# 检查环境变量
python3 -c "
from src.config import settings
print(f'✅ 应用名称: {settings.app_name}')
print(f'✅ ZhipuAI: {\"已配置\" if settings.zhipuai.api_key else \"未配置\"}')
print(f'✅ PostgreSQL: {settings.postgres.database}')
"
```

## 🔍 常见问题排查

### 问题1: 端口被占用

```bash
# 检查端口占用
lsof -i :8000

# 杀死进程
kill -9 <PID>

# 或使用其他端口
python -m uvicorn src.api.main:app --port 8001
```

### 问题2: 模块导入失败

```bash
# 确认在项目根目录
cd /Users/wangzheng/Downloads/playDemo/AntigravityDemo/chatBI

# 激活虚拟环境
source .venv/bin/activate

# 检查Python路径
python3 -c "import sys; print('\n'.join(sys.path))"
```

### 问题3: PostgreSQL连接失败

```bash
# 检查PostgreSQL是否运行
docker compose ps postgres

# 启动PostgreSQL
docker compose up -d postgres

# 初始化数据库
bash scripts/init-postgres.sh
```

## 📝 测试检查清单

### 基础检查
- [ ] Python版本 >= 3.11
- [ ] 虚拟环境已激活
- [ ] 依赖已安装 (`pip list`)
- [ ] 环境变量已配置

### 功能检查
- [ ] 代码导入成功
- [ ] 服务器启动成功
- [ ] 健康检查通过
- [ ] API文档可访问
- [ ] v3查询API可调用

### 可选检查
- [ ] PostgreSQL已连接
- [ ] 前端界面正常显示
- [ ] 监控服务运行（Prometheus/Grafana）

## 💡 开发提示

### 查看日志

```bash
# 查看应用日志
tail -f /tmp/api_server.log

# 查看PostgreSQL日志
docker compose logs -f postgres
```

### 调试模式

```bash
# 启用详细日志
LOG_LEVEL=DEBUG python -m uvicorn src.api.main:app --reload
```

### 性能分析

```bash
# 运行基准测试
bash scripts/run-benchmark.sh

# 运行压力测试
locust -f tests/performance/load_test.py --host=http://localhost:8000
```

## 📚 更多文档

- [项目结构说明](docs/PROJECT_STRUCTURE.md)
- [运行测试报告](docs/RUNTIME_TEST_REPORT.md)
- [PostgreSQL集成指南](docs/POSTGRESQL_INTEGRATION.md)
- [监控系统指南](monitoring/README.md)

---

**快速验证你的环境！** 🎉
