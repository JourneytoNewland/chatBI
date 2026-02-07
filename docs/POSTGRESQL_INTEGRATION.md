# PostgreSQL 集成文档

## 概述

chatBI 系统集成了 PostgreSQL 作为主要的数据存储，支持完整的星型模式（Star Schema）数据仓库架构。

## 数据架构

### 维度表 (Dimensions)

| 表名 | 说明 | 关键字段 |
|------|------|---------|
| `dim_date` | 日期维度 | date_key, year, quarter, month, week, is_holiday |
| `dim_region` | 地区维度 | region_key, region_id, region_name, tier |
| `dim_category` | 品类维度 | category_key, category_id, category_name, level |
| `dim_channel` | 渠道维度 | channel_key, channel_id, channel_name, channel_type |
| `dim_user_level` | 用户等级维度 | level_key, level_id, level_name, min_points, max_points |

### 事实表 (Facts)

| 表名 | 说明 | 关键指标 |
|------|------|---------|
| `fact_orders` | 订单事实 | gmv, order_count, total_order_amount, average_order_value |
| `fact_user_activity` | 用户活跃度事实 | dau, mau, new_users, retention_day1/7/30 |
| `fact_traffic` | 流量事实 | visitors, page_views, cart_conversion_rate, order_conversion_rate |
| `fact_revenue` | 收入事实 | total_revenue, arpu, arppu, ltv_30d/90d/365d |
| `fact_finance` | 财务事实 | revenue, net_profit, gross_profit_margin, roi |

### 物化视图 (Materialized Views)

| 视图名 | 说明 | 用途 |
|--------|------|------|
| `mv_daily_gmv_by_region` | 每日GMV按地区汇总 | 地区销售分析 |
| `mv_daily_dau_by_channel` | 每日DAU按渠道汇总 | 渠道用户分析 |
| `mv_monthly_finance_summary` | 月度财务汇总 | 财务报表分析 |

## 快速开始

### 1. 启动 PostgreSQL

使用 Docker Compose 启动：

```bash
# 启动 PostgreSQL 服务
docker compose up -d postgres

# 查看日志
docker compose logs -f postgres
```

### 2. 初始化数据库

运行初始化脚本：

```bash
# 一键初始化（Schema + 测试数据）
bash init-postgres.sh
```

或分步执行：

```bash
# 1. 运行数据库迁移（创建表结构）
python -m src.database.run_migration

# 2. 初始化测试数据
python -m src.database.init_test_data
```

### 3. 验证安装

连接数据库并查看表：

```bash
# 使用 psql 连接
docker exec -it chatbi-postgres psql -U chatbi -d chatbi

# 或使用 Python 脚本测试
python -c "from src.database.postgres_client import postgres_client; postgres_client.test_connection()"
```

## 数据库配置

### 环境变量

在 `.env` 文件中配置：

```bash
# PostgreSQL 配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=chatbi
POSTGRES_USER=chatbi
POSTGRES_PASSWORD=chatbi_password
```

### 连接池配置

在 `src/config.py` 中调整连接池参数：

```python
class PostgreSQLConfig(BaseSettings):
    pool_size: int = 10              # 连接池大小
    max_overflow: int = 20           # 最大溢出连接数
    pool_timeout: int = 30           # 连接池超时(秒)
    pool_recycle: int = 3600         # 连接回收时间(秒)
```

## 使用示例

### Python 客户端使用

```python
from src.database.postgres_client import postgres_client

# 测试连接
if postgres_client.test_connection():
    print("✅ 连接成功")

# 查询数据
results = postgres_client.execute_query(
    "SELECT * FROM fact_orders WHERE date_key = %s LIMIT 10",
    (20240201,)
)

for row in results:
    print(row['gmv'], row['order_count'])

# 更新数据
affected_rows = postgres_client.execute_update(
    "UPDATE fact_orders SET gmv = %s WHERE order_key = %s",
    (100000.00, 1)
)

# 批量插入
data_list = [
    (20240201, 1, 1, 1, 1, 100, 50000.00, 1000.00, 49000.00),
    (20240201, 2, 2, 2, 2, 200, 100000.00, 2000.00, 98000.00),
]
postgres_client.execute_batch(
    """INSERT INTO fact_orders
       (date_key, region_key, category_key, channel_key, user_level_key,
        order_count, total_order_amount, total_discount, gmv)
       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
    data_list
)
```

### SQL 查询示例

#### 查询最近7天GMV

```sql
SELECT
    dd.date,
    dr.region_name,
    SUM(fo.gmv) as total_gmv,
    SUM(fo.order_count) as total_orders
FROM fact_orders fo
JOIN dim_date dd ON fo.date_key = dd.date_key
JOIN dim_region dr ON fo.region_key = dr.region_key
WHERE dd.date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY dd.date, dr.region_name
ORDER BY dd.date, total_gmv DESC;
```

#### 查询各渠道DAU

```sql
SELECT
    dc.channel_name,
    SUM(fua.dau) as total_dau,
    SUM(fua.new_users) as total_new_users,
    AVG(fua.retention_day1) as avg_retention_day1
FROM fact_user_activity fua
JOIN dim_channel dc ON fua.channel_key = dc.channel_key
JOIN dim_date dd ON fua.date_key = dd.date_key
WHERE dd.date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY dc.channel_name
ORDER BY total_dau DESC;
```

#### 查询转化率漏斗

```sql
SELECT
    dd.date,
    SUM(ft.visitors) as visitors,
    SUM(ft.add_to_cart_count) as add_to_cart,
    SUM(ft.checkout_count) as checkout,
    SUM(ft.order_count) as orders,
    SUM(ft.order_count)::DECIMAL / NULLIF(SUM(ft.visitors), 0) as conversion_rate
FROM fact_traffic ft
JOIN dim_date dd ON ft.date_key = dd.date_key
WHERE dd.date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY dd.date
ORDER BY dd.date;
```

## 性能优化

### 索引策略

系统已创建以下索引：

- **维度表索引**: year, quarter, month, week, tier, level
- **事实表索引**: date_key, (date_key, region_key), (date_key, channel_key), created_at
- **物化视图索引**: date_key, (year, month)

### 物化视图刷新

```sql
-- 刷新所有物化视图
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_gmv_by_region;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_dau_by_channel;
REFRESH MATERIALIZED VIEW mv_monthly_finance_summary;
```

### 查询优化建议

1. **使用物化视图**: 对于聚合查询，优先使用预聚合的物化视图
2. **日期范围过滤**: 始终在 date_key 上添加日期过滤条件
3. **避免 SELECT \***: 只查询需要的列
4. **使用 EXPLAIN ANALYZE**: 分析慢查询

```sql
EXPLAIN ANALYZE
SELECT * FROM fact_orders
WHERE date_key >= 20240201
LIMIT 100;
```

## 数据维护

### 数据备份

```bash
# 备份数据库
docker exec chatbi-postgres pg_dump -U chatbi chatbi > backup_$(date +%Y%m%d).sql

# 恢复数据库
docker exec -i chatbi-postgres psql -U chatbi chatbi < backup_20240201.sql
```

### 数据清理

```sql
-- 清理旧数据（保留最近90天）
DELETE FROM fact_orders
WHERE date_key < (SELECT CAST(TO_CHAR(CURRENT_DATE - INTERVAL '90 days', 'YYYYMMDD') AS INTEGER));
```

### 数据监控

```sql
-- 查看表大小
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 查看慢查询
SELECT
    query,
    calls,
    total_time,
    mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

## 故障排查

### 连接失败

```bash
# 检查容器状态
docker ps | grep chatbi-postgres

# 查看日志
docker compose logs postgres

# 检查端口占用
lsof -i :5432
```

### 性能问题

```sql
-- 查看当前连接数
SELECT count(*) FROM pg_stat_activity;

-- 查看锁等待
SELECT * FROM pg_stat_activity WHERE wait_event_type = 'Lock';

-- 查看表膨胀
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as size,
    n_live_tup,
    n_dead_tup
FROM pg_stat_user_tables
ORDER BY pg_relation_size(schemaname||'.'||tablename) DESC;
```

## 数据安全

### 权限管理

```sql
-- 创建只读用户
CREATE USER chatbi_readonly WITH PASSWORD 'readonly_password';
GRANT CONNECT ON DATABASE chatbi TO chatbi_readonly;
GRANT USAGE ON SCHEMA public TO chatbi_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO chatbi_readonly;

-- 创建数据分析师用户
CREATE USER chatbi_analyst WITH PASSWORD 'analyst_password';
GRANT CONNECT ON DATABASE chatbi TO chatbi_analyst;
GRANT USAGE ON SCHEMA public TO chatbi_analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO chatbi_analyst;
```

### 数据加密

PostgreSQL 数据加密建议：

1. **传输加密**: 使用 SSL/TLS 连接
2. **存储加密**: 使用文件系统级加密（如 LUKS）
3. **备份加密**: 加密备份文件

```bash
# SSL 连接示例
psql "host=localhost port=5432 dbname=chatbi user=chatbi sslmode=require"
```

## 下一步

- [ ] 实现SQL生成器（MQL → SQL）
- [ ] 改造MQL引擎以使用真实数据
- [ ] 实现智能解读模块
- [ ] 性能基准测试

## 参考资料

- [PostgreSQL 官方文档](https://www.postgresql.org/docs/)
- [Docker Hub - postgres](https://hub.docker.com/_/postgres)
- [Psycopg2 文档](https://www.psycopg.org/docs/)
