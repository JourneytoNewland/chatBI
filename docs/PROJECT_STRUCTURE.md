# chatBI 项目结构说明

## 整理说明 (2026-02-07)

为了提升项目可维护性，进行了以下整理工作：

### 1. 清理的内容

#### 日志文件（已删除）
- ❌ `api.log` (113KB)
- ❌ `api_bge.log` (495B)
- ❌ `api_clean.log` (247B)
- ❌ `api_complete.log` (227KB)

#### 历史文档（已归档到 `docs/archive/`）
- 📦 `API_DOCUMENTATION.md`
- 📦 `API_QUICK_REFERENCE.md`
- 📦 `CONFIGURATION_GUIDE.md`
- 📦 `DOCKER.md`
- 📦 `DOCKER_FIX.md`
- 📦 `FINAL_ACCEPTANCE_REPORT.md`
- 📦 `FINAL_TEST_GUIDE.md`
- 📦 `FRONTEND_GUIDE.md`
- 📦 `IMPLEMENTATION_PLAN.md`
- 📦 `INTENT_RECOGNITION_FIX_REPORT.md`
- 📦 `OPTIMIZATION_PLAN.md`
- 📦 `OPTIMIZATION_SUMMARY.md`
- 📦 `QUICKSTART.md`
- 📦 `QUICK_FIX.md`
- 📦 `QUICK_START.md`
- 📦 `REAL_DATA_INTEGRATION_SUMMARY.md`
- 📦 `SECURITY_AUDIT_REPORT.md`
- 📦 `SECURITY_FIX_REPORT.md`
- 📦 `START_GUIDE.md`
- 📦 `SYSTEM_STATUS.md`
- 📦 `TEST_GUIDE.md`
- 📦 `TEST_REPORT_*.md`
- 📦 `UPDATE_SUMMARY.md`
- 📦 `POSTGRES_INTEGRATION_STATUS.md`

### 2. 脚本分类整理

#### `scripts/monitoring/` - 监控脚本
- `run-benchmark.sh` - 性能基准测试
- `run-monitoring.sh` - 启动监控服务

#### `scripts/setup/` - 安装配置脚本
- `fix-and-start.sh` - 修复并启动
- `start-backend.sh` - 启动后端服务
- `start-docker.sh` - 启动Docker服务
- `start-local.sh` - 启动本地服务
- `start.sh` - 通用启动脚本

#### `scripts/testing/` - 测试脚本
- `deep-diagnose.sh` - 深度诊断
- `docker-diagnostic.sh` - Docker诊断
- `test-graph-features.sh` - 测试图谱功能
- `test_all_queries.sh` - 测试所有查询

#### `scripts/` - 主要脚本
- `run_demo.sh` - 启动演示服务器
- `demo-complete-system.sh` - 演示完整系统
- `open-dashboard.sh` - 打开仪表板
- `test-zhipu.sh` - 测试智谱AI
- `init-postgres.sh` - 初始化PostgreSQL

### 3. 新的目录结构

```
chatBI/
├── docs/                      # 📚 文档
│   ├── archive/              # 📦 历史文档归档（20+个文件）
│   ├── POSTGRESQL_INTEGRATION.md
│   └── PROJECT_STRUCTURE.md  # 本文档
│
├── scripts/                   # 🔧 脚本（已分类）
│   ├── setup/                # 安装配置
│   ├── monitoring/           # 监控脚本
│   └── testing/              # 测试脚本
│
├── src/                       # 💻 源代码
│   ├── api/
│   ├── inference/
│   ├── mql/
│   ├── database/
│   ├── monitoring/
│   └── ...
│
├── tests/                     # 🧪 测试
│   └── performance/
│
├── monitoring/                # 📊 监控配置
│   ├── prometheus/
│   └── grafana/
│
├── frontend/                  # 🎨 前端
├── docker-compose.yml         # 🐳 Docker编排
├── requirements.txt           # 📦 Python依赖
└── README.md                  # 📖 主文档（已更新）
```

### 4. .gitignore 更新

新增忽略规则：
```gitignore
# 日志文件
*.log
api_*.log
*.log.*
```

### 5. README 更新

主README已完全重写，包含：
- ✅ 核心特性介绍
- ✅ 快速开始指南
- ✅ API使用示例
- ✅ 支持的指标列表
- ✅ 项目结构说明
- ✅ 配置说明
- ✅ 性能指标
- ✅ 监控看板访问
- ✅ 测试指南
- ✅ 文档链接

### 6. 根目录清理

整理后根目录只保留：
- ✅ 核心配置文件（`docker-compose.yml`, `requirements.txt`等）
- ✅ 主文档（`README.md`, `CLAUDE.md`等）
- ✅ 必要脚本（`run-production-server.py`等）
- ❌ 移除了18个散落的脚本文件
- ❌ 移除了24个历史文档文件
- ❌ 删除了4个日志文件

## 使用指南

### 启动服务

```bash
# 演示模式（推荐）
bash scripts/run_demo.sh

# 完整模式
docker compose up -d
bash scripts/init-postgres.sh
python run-production-server.py

# 监控服务
bash scripts/run-monitoring.sh
```

### 查看文档

```bash
# 主文档
cat README.md

# PostgreSQL集成
cat docs/POSTGRESQL_INTEGRATION.md

# 监控系统
cat monitoring/README.md

# 历史文档
ls docs/archive/
```

### 运行测试

```bash
# 性能基准测试
bash scripts/run-benchmark.sh

# 压力测试
locust -f tests/performance/load_test.py --host=http://localhost:8000
```

## 后续建议

1. **定期清理** - 每月检查并清理临时文件
2. **文档归档** - 完成的阶段文档移到`docs/archive/`
3. **脚本整理** - 新脚本按功能分类放置
4. **README更新** - 重大功能更新时同步更新README
5. **日志管理** - 使用`logger`模块，避免文件日志

## 总结

通过这次整理：
- ✅ 清理了4个日志文件（~350KB）
- ✅ 归档了24个历史文档
- ✅ 分类整理了18个脚本文件
- ✅ 更新了主README文档
- ✅ 完善了.gitignore配置

项目结构更加清晰，便于维护和协作！
