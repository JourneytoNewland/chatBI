# 监控系统指南

## 概述

chatBI系统集成了Prometheus + Grafana的完整监控体系，提供：

- **实时监控**: 系统性能、业务指标
- **告警通知: 异常情况及时响应
- **可视化**: 直观的图表和仪表板
- **数据存储**: 长期历史数据查询

## 架构

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  chatBI API │ ──> │  Prometheus  │ ──> │   Grafana   │
│   :8000     │     │    :9090     │     │    :3000    │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ├─ PostgreSQL
                           ├─ Qdrant
                           └─ Neo4j
```

## 快速开始

### 1. 启动监控服务

```bash
# 启动所有服务（包括Prometheus和Grafana）
docker compose up -d

# 查看服务状态
docker compose ps
```

### 2. 访问监控界面

**Prometheus**: http://localhost:9090
- 查询原始指标数据
- 执行PromQL查询
- 查看告警规则

**Grafana**: http://localhost:3000
- 默认用户名: `admin`
- 默认密码: `admin`
- 预配置数据源: Prometheus
- 预配置看板: chatBI 系统概览

### 3. 配置API服务

在API服务中添加`/metrics`端点：

```python
from prometheus_client import start_http_server
from src.monitoring.metrics import registry

# 启动Prometheus metrics服务器
start_http_server(8001, registry=registry)

# 或在FastAPI中集成
from prometheus_client import make_asgi_app

metrics_app = make_asgi_app(registry=registry)
app.mount("/metrics", metrics_app)
```

## 监控指标

### 查询指标

| 指标名称 | 类型 | 说明 |
|---------|------|------|
| `chatbi_queries_total` | Counter | 查询总数 |
| `chatbi_query_duration_seconds` | Histogram | 查询延迟分布 |
| `chatbi_queries_in_progress` | Gauge | 当前正在处理的查询数 |

### 意图识别指标

| 指标名称 | 类型 | 说明 |
|---------|------|------|
| `chatbi_intent_recognition_total` | Counter | 意图识别总数 |
| `chatbi_intent_recognition_duration_seconds` | Histogram | 意图识别延迟 |
| `chatbi_intent_accuracy` | Gauge | 意图识别准确率 |

### 数据库指标

| 指标名称 | 类型 | 说明 |
|---------|------|------|
| `chatbi_db_queries_total` | Counter | 数据库查询总数 |
| `chatbi_db_query_duration_seconds` | Histogram | 数据库查询延迟 |
| `chatbi_db_pool_size` | Gauge | 数据库连接池大小 |
| `chatbi_db_pool_available` | Gauge | 可用连接数 |

### 业务指标

| 指标名称 | 类型 | 说明 |
|---------|------|------|
| `chatbi_metric_usage_total` | Counter | 指标使用频率 |
| `chatbi_cache_hit_rate` | Gauge | 缓存命中率 |
| `chatbi_llm_requests_total` | Counter | LLM调用总数 |
| `chatbi_llm_tokens_total` | Counter | LLM Token消耗 |

## Grafana看板

### chatBI 系统概览

访问路径: http://localhost:3000/d/chatbi-overview

**面板说明**:

1. **查询速率 (QPS)** - 当前每秒查询数
2. **查询错误率** - 失败请求百分比
3. **P95查询延迟** - 95%分位延迟
4. **查询延迟分布** - P50/P95/P99延迟曲线
5. **查询请求量** - 成功/失败请求趋势
6. **Top 10 指标** - 最常用的业务指标
7. **数据库连接池** - PostgreSQL连接使用情况
8. **LLM Token消耗** - 提示词/完成Token使用量

## 告警规则

### 配置的告警

| 告警名称 | 触发条件 | 级别 | 说明 |
|---------|---------|------|------|
| `HighQueryLatency` | P95延迟 > 1秒 | warning | 查询响应慢 |
| `HighErrorRate` | 错误率 > 5% | critical | 服务异常 |
| `HighIntentLatency` | LLM意图识别 > 5秒 | warning | LLM响应慢 |
| `DatabasePoolExhausted` | 可用连接 < 2 | critical | 连接池耗尽 |
| `HighLLMErrorRate` | LLM失败率 > 10% | warning | LLM服务异常 |
| `HighMemoryUsage` | 内存使用 > 2GB | warning | 内存占用高 |

### 查看告警

在Prometheus中查看: http://localhost:9090/alerts

### 配置告警通知

编辑 `monitoring/prometheus/alerts/chatbi-alerts.yml` 添加：

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093
```

## 常用查询

### Prometheus查询示例

```promql
# 查询QPS
sum(rate(chatbi_queries_total[5m]))

# 查询P95延迟
histogram_quantile(0.95, chatbi_query_duration_seconds_bucket)

# 查询错误率
sum(rate(chatbi_queries_total{status="error"}[5m])) / sum(rate(chatbi_queries_total[5m])) * 100

# 查询Top 5指标
topk(5, sum by (metric_name)(chatbi_metric_usage_total))

# 查询数据库连接池使用率
(1 - chatbi_db_pool_available{database="postgresql"} / chatbi_db_pool_size{database="postgresql"}) * 100

# 查询LLM成本
sum(chatbi_llm_tokens_total{type="prompt"} / 1000) * 0.0001
```

## 性能基准

### 目标指标

| 指标 | 目标值 | 当前值 |
|------|--------|--------|
| P50延迟 | <100ms | - |
| P95延迟 | <300ms | - |
| P99延迟 | <500ms | - |
| 错误率 | <1% | - |
| QPS | >100 | - |

### 监控最佳实践

1. **设置合理的时间范围**
   - 实时监控: 最近5分钟
   - 趋势分析: 最近1小时
   - 容量规划: 最近7天

2. **关注关键指标**
   - P95延迟比平均延迟更重要
   - 错误率比绝对错误数更重要
   - 资源使用率趋势

3. **告警阈值调整**
   - 根据实际业务调整阈值
   - 避免告警疲劳
   - 分级告警（warning/critical）

## 故障排查

### 1. 无法访问Grafana

```bash
# 检查容器状态
docker compose ps grafana

# 查看日志
docker compose logs grafana

# 重启服务
docker compose restart grafana
```

### 2. Prometheus无法抓取指标

```bash
# 检查API服务/metrics端点
curl http://localhost:8000/metrics

# 检查Prometheus配置
docker exec -it chatbi-prometheus cat /etc/prometheus/prometheus.yml

# 查看Prometheus目标状态
# 访问 http://localhost:9090/targets
```

### 3. 数据不显示

- 确认API服务正在运行
- 确认Prometheus能抓取到指标
- 确认Grafana数据源配置正确
- 检查时间范围设置

## 扩展阅读

- [Prometheus官方文档](https://prometheus.io/docs/)
- [Grafana官方文档](https://grafana.com/docs/)
- [PromQL查询语言](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana看板最佳实践](https://grafana.com/docs/grafana/latest/best-practices/)

## 下一步

- [ ] 配置Alertmanager告警通知
- [ ] 添加更多业务指标
- [ ] 创建自定义看板
- [ ] 集成日志聚合（ELK/Loki）
- [ ] 配置分布式追踪（Jaeger/Zipkin）
