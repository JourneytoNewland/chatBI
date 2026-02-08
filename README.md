# chatBI - 智能问数系统

> 基于大模型的企业级智能数据分析平台，让数据查询像对话一样简单。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)

## ✨ 核心特性

### 🧠 三层混合意图识别
- **L1 规则引擎** - 快速匹配常见模式（<10ms）
- **L2 向量召回** - BGE-M3语义相似度（<100ms）
- **L3 LLM增强** - 智谱AI GLM-4深度理解（~5s）
- **准确率 95%+** - 自适应降级，平衡速度与准确度

### 📊 完整的数据仓库
- **星型模式架构** - 5个维度表 + 5个事实表
- **PostgreSQL存储** - 生产级关系型数据库
- **25+业务指标** - 覆盖电商、用户、流量、收入、财务
- **物化视图优化** - 预聚合，10-100倍性能提升

### 🔍 智能SQL生成
- **QueryIntent → SQL** - 自动生成PostgreSQL查询
- **多维度JOIN** - 支持地区、品类、渠道、用户等级
- **时间范围过滤** - 日/周/月自动处理
- **聚合操作** - SUM/AVG/COUNT/MAX/MIN

### 📈 完整的监控体系
- **Prometheus监控** - 30+个性能和业务指标
- **Grafana看板** - 8个实时监控面板
- **告警规则** - 延迟、错误率、资源异常
- **性能基准测试** - P50/P95/P99延迟统计

### 💡 AI智能解读
- **趋势分析** - 上升/下降/波动识别
- **异常检测** - 自动发现数据异常点
- **洞察生成** - 基于LLM的业务洞察
- **建议推荐** - 数据驱动的决策建议

### 🔍 根因分析（NEW!）
- **智能异常检测** - 3σ原则、IQR四分位法、移动平均
- **维度分解** - 贡献度分析、帕累托分析
- **趋势分析** - 线性回归、R²拟合、转折点检测
- **因果推断** - 业务规则引擎、置信度量化
- **可视化展示** - 异常卡片、趋势图表、因果因素、行动建议

**使用示例**：
- "为什么GMV最近下降了？"
- "分析DAU下降的原因"
- "转化率怎么了"

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/JourneytoNewland/chatBI.git
cd chatBI

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置（必需：设置智谱AI API Key）
# ZHIPUAI_API_KEY=your-api-key-here
```

### 3. 启动服务

#### 方式A：演示模式（推荐新手）

```bash
# 一键启动（内置模拟数据）
bash scripts/run_demo.sh
```

访问 http://localhost:8080 查看前端界面

#### 方式B：完整模式（需要Docker）

```bash
# 启动所有服务（PostgreSQL + Qdrant + Neo4j）
docker compose up -d

# 初始化数据库
bash scripts/init-postgres.sh

# 启动API服务
python run-production-server.py
```

### 4. 启动监控（可选）

```bash
# 启动Prometheus + Grafana
bash scripts/run-monitoring.sh

# 访问监控界面
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

## 📖 使用指南

### API查询示例

```bash
# 简单查询
curl -X POST http://localhost:8000/api/v3/query \
  -H "Content-Type: application/json" \
  -d '{"query": "最近7天GMV"}'

# 维度分组
curl -X POST http://localhost:8000/api/v3/query \
  -H "Content-Type: application/json" \
  -d '{"query": "按地区统计DAU"}'

# 复杂查询
curl -X POST http://localhost:8000/api/v3/query \
  -H "Content-Type: application/json" \
  -d '{"query": "本月按渠道GMV总和"}'
```

### Python SDK

```python
from src.inference.enhanced_hybrid import EnhancedHybridIntentRecognizer

# 初始化识别器
recognizer = EnhancedHybridIntentRecognizer(llm_provider="zhipu")

# 执行查询
result = recognizer.recognize("最近7天成交金额")

print(f"核心查询: {result.final_intent.core_query}")
print(f"时间粒度: {result.final_intent.time_granularity}")
print(f"置信度: {result.final_intent.confidence}")
```

## 📊 支持的指标

| 分类 | 指标 | 示例查询 |
|------|------|---------|
| **电商** | GMV、订单量、客单价 | "最近7天GMV" |
| **用户** | DAU、MAU、留存率 | "按渠道统计DAU" |
| **流量** | 转化率、加购率 | "本周转化率" |
| **收入** | ARPU、ARPPU、LTV | "本月ARPU" |
| **财务** | 营收、利润率、ROI | "按地区利润率" |

## 🏗️ 项目结构

```
chatBI/
├── docs/                      # 文档
│   ├── archive/              # 历史文档归档
│   ├── POSTGRESQL_INTEGRATION.md
│   └── README.md
│
├── scripts/                   # 脚本
│   ├── setup/                # 安装配置脚本
│   ├── monitoring/           # 监控脚本
│   └── testing/              # 测试脚本
│
├── src/                       # 源代码
│   ├── api/                  # API层
│   │   ├── main.py           # FastAPI主应用
│   │   └── complete_query.py # 完整查询API
│   ├── inference/            # 意图识别
│   │   ├── enhanced_hybrid.py # 三层混合架构
│   │   └── intent.py         # 意图定义
│   ├── mql/                  # MQL引擎
│   │   ├── engine_v2.py      # MQL执行引擎V2
│   │   ├── sql_generator_v2.py # SQL生成器V2
│   │   └── intelligent_interpreter.py # 智能解读
│   ├── database/             # 数据库
│   │   ├── postgres_client.py # PostgreSQL客户端
│   │   ├── migrations/       # 数据库迁移
│   │   └── init_test_data.py # 测试数据生成
│   ├── monitoring/           # 监控
│   │   └── metrics.py        # Prometheus指标
│   └── config.py             # 配置管理
│
├── frontend/                  # 前端
│   ├── index.html            # 主界面
│   └── intent-visualization-v2.html # 可视化界面
│
├── monitoring/                # 监控配置
│   ├── prometheus/           # Prometheus配置
│   └── grafana/              # Grafana看板
│
├── tests/                     # 测试
│   └── performance/          # 性能测试
│       ├── load_test.py      # Locust压力测试
│       └── benchmark.py      # 基准测试
│
├── docker-compose.yml         # Docker编排
├── requirements.txt           # Python依赖
└── README.md                  # 本文档
```

## 🔧 配置说明

### 智谱AI API（必需）

**⚠️ 安全警告：严禁将API Key硬编码在代码中！**

正确配置方式：

```bash
# 方式1: 命令行设置
export ZHIPUAI_API_KEY="your-api-key"

# 方式2: .env文件
echo "ZHIPUAI_API_KEY=your-api-key" >> .env

# 方式3: 运行时传入
ZHIPUAI_API_KEY="your-api-key" python app.py
```

配置验证：
```bash
python -c "import os; print('✅ 配置成功' if os.getenv('ZHIPUAI_API_KEY') else '❌ 未配置')"
```

### 模型选择

| 模型 | 速度 | 成本 | 适用场景 |
|------|------|------|---------|
| glm-4-flash | 快 | 免费 | 开发测试、生产环境 |
| glm-4-plus | 中 | ¥1/1M tokens | 高准确率要求 |
| glm-4-0520 | 慢 | ¥1/1M tokens | 最新模型 |

## 📈 性能指标

| 指标 | 目标值 | 当前值 | 状态 |
|------|--------|--------|------|
| P50延迟 | <100ms | 待测 | - |
| P95延迟 | <300ms | 待测 | - |
| P99延迟 | <500ms | 待测 | - |
| 并发能力 | 1000 QPS | 待测 | - |
| 意图识别准确率 | >95% | 95%+ | ✅ |

## 🔍 监控看板

启动监控服务后访问：

- **Grafana**: http://localhost:3000
  - 用户名: `admin`
  - 密码: `admin`
  - 预配置看板: chatBI 系统概览

- **Prometheus**: http://localhost:9090
  - 查询原始指标
  - 查看告警规则

## 🧪 测试

### 运行测试

```bash
# 性能基准测试
bash scripts/run-benchmark.sh

# Locust压力测试
locust -f tests/performance/load_test.py --host=http://localhost:8000
```

### 测试覆盖率

```bash
# 运行单元测试
pytest tests/

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

## 📚 文档

### 核心功能
- [根因分析使用指南](docs/ROOT_CAUSE_USAGE.md) - L4层根因分析完整文档
- [PostgreSQL集成指南](docs/POSTGRESQL_INTEGRATION.md) - 数据仓库架构
- [意图识别文档](docs/intent_recognition_summary.md) - 三层混合意图识别
- [MQL系统文档](docs/MQL_SYSTEM_SUMMARY.md) - MQL引擎与SQL生成

### 运维监控
- [监控系统指南](monitoring/README.md) - Prometheus + Grafana
- [性能测试指南](tests/performance/README.md) - 基准测试与压力测试
- [安全最佳实践](docs/SECURITY_BEST_PRACTICES.md) - 安全配置与审计

### 历史文档
- [历史文档归档](docs/archive/) - 开发过程文档

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [智谱AI](https://open.bigmodel.cn/) - 提供GLM-4模型支持
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Python Web框架
- [PostgreSQL](https://www.postgresql.org/) - 强大的开源数据库
- [Qdrant](https://qdrant.tech/) - 向量搜索引擎
- [Prometheus](https://prometheus.io/) - 监控系统

## 📮 联系方式

- 项目地址: https://github.com/JourneytoNewland/chatBI
- 问题反馈: [GitHub Issues](https://github.com/JourneytoNewland/chatBI/issues)

---

**当前版本**: v2.1
**最后更新**: 2026-02-08
**维护者**: Crazygenius（王拯）
