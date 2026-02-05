# PostgreSQL集成与智能解读 - 部署指南

## 概述

本文档介绍如何部署和使用PostgreSQL集成与智能解读功能。

## 架构

```
用户查询 → 语义检索(Qdrant+Neo4j) → 意图识别 → MQL生成 → PostgreSQL执行 → 智能解读(LLM) → 结果返回
```

## 快速开始

### 1. 启动所有服务

```bash
# 启动PostgreSQL、Qdrant、Neo4j
docker-compose up -d

# 验证PostgreSQL启动
docker-compose logs postgres
```

### 2. 初始化测试数据

```bash
python scripts/init_test_data.py
```

这将生成30天的测试数据：
- 订单事实表: ~10,000条
- 用户活动事实表: ~50,000条
- 流量事实表: ~30,000条
- 营收事实表: ~1,000条
- 财务事实表: ~2,000条

### 3. 运行集成测试

```bash
python scripts/test_postgres_integration.py
```

测试内容：
- PostgreSQL连接测试
- 健康检查测试
- 基础查询测试
- 聚合查询测试
- 分组查询测试
- 过滤查询测试
- 性能测试（100次查询，平均<500ms）
- 智能解读测试

### 4. 启动API服务

```bash
python -m src.api.v2_query_api
```

访问：http://localhost:8000

## 数据库Schema

### 维度表

- `dim_date`: 时间维度表
- `dim_region`: 地区维度表（华东、华南、华北、西南、东北）
- `dim_category`: 品类维度表（电子产品、服装等）
- `dim_channel`: 渠道维度表（APP、小程序、H5、PC）
- `dim_user_level`: 用户等级维度表（普通、白银、黄金、钻石）

### 事实表

- `fact_orders`: 订单事实表（GMV、订单量、客单价等）
- `fact_user_activity`: 用户活动事实表（DAU、MAU、留存率等）
- `fact_traffic`: 流量事实表（转化率、加购率、支付率）
- `fact_revenue`: 营收事实表（ARPU、LTV）
- `fact_finance`: 财务事实表（营收、利润、利润率）

## API使用示例

### 1. 基础查询

```bash
curl -X POST http://localhost:8000/api/v2/query \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "最近7天GMV总和"
  }'
```

### 2. 分组查询

```bash
curl -X POST http://localhost:8000/api/v2/query \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "最近7天按地区统计GMV"
  }'
```

### 3. 过滤查询

```bash
curl -X POST http://localhost:8000/api/v2/query \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "最近7天华东地区的GMV"
  }'
```

## 响应格式

```json
{
  "query": "最近7天GMV总和",
  "intent": {
    "core_query": "GMV",
    "time_range": {
      "start": "2024-01-01",
      "end": "2024-01-07"
    },
    "aggregation_type": "SUM"
  },
  "mql": "GMV[SUM](2024-01-01 TO 2024-01-07)",
  "result": {
    "sql": "SELECT SUM(f.order_amount) AS value FROM fact_orders f ...",
    "result": [
      {
        "date": "2024-01-01",
        "value": 523456.78,
        "metric": "GMV",
        "unit": "元"
      }
    ],
    "row_count": 1,
    "execution_time_ms": 234
  },
  "interpretation": {
    "summary": "GMV呈上升趋势，7天内增长15.2%，平均每天增长2.2%。",
    "trend": "upward",
    "key_findings": [
      "GMV从45万增长到52万，增长15.2%",
      "平均每天增长2.2%，增速稳定",
      "最低值45万，最高值52万"
    ],
    "insights": [
      "增长趋势可能受促销活动影响",
      "华东地区贡献最大，占比40%"
    ],
    "suggestions": [
      "继续当前营销策略",
      "关注华东地区客户需求变化"
    ],
    "confidence": 0.82,
    "data_analysis": {
      "trend": "upward",
      "change_rate": 15.2,
      "volatility": 8.5,
      "min": 450000,
      "max": 520000,
      "avg": 485000
    }
  },
  "execution_time_ms": 1234
}
```

## 环境变量配置

在`.env`文件中配置：

```bash
# PostgreSQL配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=chatbi
POSTGRES_USER=chatbi
POSTGRES_PASSWORD=chatbi_password
POSTGRES_POOL_SIZE=10

# ZhipuAI配置（用于智能解读）
ZHIPUAI_API_KEY=your_api_key_here
ZHIPUAI_MODEL=glm-4-flash
```

## 性能优化

### 1. 索引优化

Schema已包含关键索引：
- 事实表外键索引
- 日期字段索引
- 考虑部分索引（只索引最近30天）

### 2. 连接池调优

根据并发量调整：
```python
POSTGRES_POOL_SIZE=10  # 连接池大小
POSTGRES_MAX_OVERFLOW=20  # 最大溢出连接数
```

### 3. 查询优化

- 使用`EXPLAIN ANALYZE`分析慢查询
- 避免SELECT *
- 合理使用LIMIT

## 故障排查

### PostgreSQL连接失败

```bash
# 检查PostgreSQL状态
docker-compose ps postgres

# 查看日志
docker-compose logs postgres

# 测试连接
docker exec -it chatbi-postgres psql -U chatbi -d chatbi -c "SELECT 1"
```

### 智能解读失败

智能解读失败不影响主查询，降级到模板解读。检查：

1. ZhipuAI API Key配置
2. 网络连接
3. 日志中的错误信息

### 性能问题

1. 检查慢查询日志
2. 分析执行计划
3. 调整连接池大小
4. 考虑增加索引

## 监控指标

### 关键指标

- 查询响应时间: <500ms（平均）
- 智能解读生成时间: <3s
- 并发查询支持: ≥10 QPS
- 数据库连接池使用率

### 日志

- 慢查询日志: >1s的查询
- 错误日志: PostgreSQL失败、LLM失败
- 降级日志: 降级到模拟数据/模板解读

## 测试

### 单元测试

```bash
# 测试PostgreSQL客户端
pytest tests/test_database/test_postgres_client.py -v

# 测试SQL生成器
pytest tests/test_mql/test_sql_generator.py -v

# 测试智能解读器
pytest tests/test_mql/test_intelligent_interpreter.py -v
```

### 集成测试

```bash
# 测试MQL与PostgreSQL集成
pytest tests/test_integration/test_mql_postgres.py -v

# 端到端验证
python scripts/test_postgres_integration.py
```

## 常见问题

### Q: 如何添加新的指标？

A: 在`src/mql/metrics.py`中注册新指标，包括：
- `metric_id`: 唯一标识
- `name`: 中文名称
- `data_source`: 数据源表
- `calculation_type`: 计算类型（SUM/COUNT/AVG）
- `formula`: 计算公式

### Q: 如何自定义智能解读模板？

A: 修改`src/mql/intelligent_interpreter.py`中的模板方法：
- `_generate_default_summary()`
- `_generate_default_findings()`
- `_generate_default_insights()`
- `_generate_default_suggestions()`

### Q: 如何禁用智能解读？

A: 在`src/api/v2_query_api.py`中注释掉智能解读部分：

```python
# 4. 智能解读（注释掉）
# interpretation = intelligent_interpreter.interpret(...)
# interpretation_dict = interpretation.model_dump()
interpretation_dict = None  # 直接设置为None
```

## 下一步

1. **生产环境部署**
   - 配置PostgreSQL主从复制
   - 设置备份策略
   - 配置监控告警

2. **功能扩展**
   - 添加更多指标
   - 支持更复杂的分析（同比、环比）
   - 优化LLM提示词

3. **性能优化**
   - 实现查询缓存
   - 优化批量查询
   - 数据库分库分表

## 技术支持

如有问题，请查看：
- 项目文档: `docs/`
- API文档: http://localhost:8000/docs
- 日志文件: 控制台输出
