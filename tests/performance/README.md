# 性能基准测试

## 概述

本目录包含chatBI系统的性能基准测试工具，用于：
1. 建立性能baseline（P50/P95/P99延迟）
2. 压力测试（并发能力）
3. 性能回归检测

## 快速开始

### 1. 安装依赖

```bash
pip install locust requests
```

### 2. 启动服务

```bash
# 方式1: 使用演示服务器
bash run_demo.sh

# 方式2: 使用生产服务器
python run-production-server.py
```

### 3. 运行基准测试

#### 方式A: Python基准测试（推荐）

```bash
# 一键运行
bash run-benchmark.sh

# 或手动运行
python tests/performance/benchmark.py
```

**输出示例**:
```
🚀 chatBI 性能基准测试套件
目标服务器: http://localhost:8000
测试查询数: 12

[1/12] 🔄 运行基准测试: GMV
   ⏳ 预热中...
   ⏳ 基准测试中...
   ✅ 测试完成
   成功率: 50/50 (100.0%)
   延迟统计:
     P50:  245.32ms
     P95:  312.45ms
     P99:  356.78ms
     平均: 248.91ms
   吞吐量: 4.02 RPS
```

#### 方式B: Locust压力测试

```bash
# Web UI模式
locust -f tests/performance/load_test.py --host=http://localhost:8000

# 访问 http://localhost:8089

# 无头模式
locust -f tests/performance/load_test.py --headless \
  --users=100 \
  --spawn-rate=10 \
  -t 1m \
  --host=http://localhost:8000
```

## 测试场景

### 1. 简单查询
- GMV、DAU、营收等单指标查询
- 无时间范围、无维度分组
- 预期延迟: <100ms

### 2. 时间范围查询
- 最近7天、本月、最近30天
- 需要日期过滤和聚合
- 预期延迟: <200ms

### 3. 维度分组查询
- 按地区、渠道、品类分组
- 需要JOIN维度表和GROUP BY
- 预期延迟: <300ms

### 4. 复杂查询
- 时间范围 + 维度分组 + 聚合
- 多表JOIN + 复杂过滤
- 预期延迟: <500ms

## 性能目标

| 指标 | 目标值 | 当前值 | 状态 |
|------|--------|--------|------|
| P50延迟 | <100ms | - | 待测试 |
| P95延迟 | <300ms | - | 待测试 |
| P99延迟 | <500ms | - | 待测试 |
| 并发能力 | 1000 QPS | - | 待测试 |
| 成功率 | >99% | - | 待测试 |

## 测试结果

测试结果保存在 `tests/performance/results/` 目录：

```
results/
├── benchmark_20240207_143022.json  # Python基准测试结果
└── locust_stats_20240207_143022.csv # Locust测试结果
```

### 结果示例

```json
{
  "name": "GMV",
  "total_runs": 50,
  "successful_runs": 50,
  "failed_runs": 0,
  "success_rate": "100.00%",
  "latency_ms": {
    "p50": "245.32",
    "p75": "278.91",
    "p95": "312.45",
    "p99": "356.78",
    "avg": "248.91",
    "min": "198.23",
    "max": "378.45"
  },
  "throughput_rps": "4.02",
  "errors": []
}
```

## 性能分析

### 查看慢查询

```python
# 分析结果文件
import json

with open('tests/performance/results/benchmark_xxx.json') as f:
    results = json.load(f)

# 找出P95延迟超过300ms的查询
slow_queries = [r for r in results if float(r['latency_ms']['p95']) > 300]

for query in slow_queries:
    print(f"{query['name']}: P95={query['latency_ms']['p95']}ms")
```

### 性能优化建议

1. **数据库索引优化**
   - 添加复合索引
   - 优化查询计划
   - 使用EXPLAIN ANALYZE

2. **缓存层**
   - Redis缓存热点数据
   - 物化视图预聚合
   - 查询结果缓存

3. **并发优化**
   - 连接池调优
   - 异步查询
   - 数据库读写分离

4. **代码优化**
   - 减少不必要的字段
   - 优化JOIN顺序
   - 使用批量操作

## 持续集成

将性能测试集成到CI/CD流程：

```yaml
# .github/workflows/performance.yml
name: Performance Test

on:
  pull_request:
    branches: [main]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install locust requests
      - name: Start server
        run: python run-production-server.py &
      - name: Run benchmark
        run: python tests/performance/benchmark.py
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: tests/performance/results/
```

## 参考资料

- [Locust官方文档](https://docs.locust.io/)
- [PostgreSQL性能优化](https://www.postgresql.org/docs/current/performance-tips.html)
- [Python性能分析](https://docs.python.org/3/library/profile.html)
