"""Prometheus监控指标定义."""

from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_client import CollectorRegistry
import os


# 创建自定义Registry（支持多实例）
registry = CollectorRegistry()


# ============================================
# 查询指标
# ============================================

# 查询总数（按状态、查询类型分类）
query_counter = Counter(
    'chatbi_queries_total',
    'Total queries processed',
    ['status', 'query_type'],  # status: success/error, query_type: simple/time_range/dimension/complex
    registry=registry
)

# 查询延迟分布（按查询类型分类）
query_duration = Histogram(
    'chatbi_query_duration_seconds',
    'Query duration in seconds',
    ['query_type'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=registry
)

# 当前正在处理的查询数
query_in_progress = Gauge(
    'chatbi_queries_in_progress',
    'Number of queries currently being processed',
    registry=registry
)


# ============================================
# 意图识别指标
# ============================================

# 意图识别请求总数
intent_recognition_counter = Counter(
    'chatbi_intent_recognition_total',
    'Total intent recognition requests',
    ['layer', 'success'],  # layer: l1/l2/l3, success: true/false
    registry=registry
)

# 意图识别延迟
intent_recognition_duration = Histogram(
    'chatbi_intent_recognition_duration_seconds',
    'Intent recognition duration in seconds',
    ['layer'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
    registry=registry
)

# 意图识别准确率
intent_accuracy = Gauge(
    'chatbi_intent_accuracy',
    'Intent recognition accuracy rate',
    ['layer'],
    registry=registry
)


# ============================================
# 数据库指标
# ============================================

# 数据库查询总数
db_query_counter = Counter(
    'chatbi_db_queries_total',
    'Total database queries',
    ['operation', 'table'],  # operation: select/insert/update/delete
    registry=registry
)

# 数据库查询延迟
db_query_duration = Histogram(
    'chatbi_db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=registry
)

# 数据库连接池使用情况
db_pool_size = Gauge(
    'chatbi_db_pool_size',
    'Database connection pool size',
    ['database'],  # postgresql/qdrant/neo4j
    registry=registry
)

db_pool_available = Gauge(
    'chatbi_db_pool_available',
    'Database connection pool available connections',
    ['database'],
    registry=registry
)


# ============================================
# 系统指标
# ============================================

# 活跃用户数
active_users = Gauge(
    'chatbi_active_users',
    'Number of active users',
    registry=registry
)

# 内存使用
memory_usage = Gauge(
    'chatbi_memory_usage_bytes',
    'Memory usage in bytes',
    registry=registry
)

# CPU使用率
cpu_usage = Gauge(
    'chatbi_cpu_usage_percent',
    'CPU usage percentage',
    registry=registry
)


# ============================================
# 业务指标
# ============================================

# 指标使用频率（Top指标）
metric_usage = Counter(
    'chatbi_metric_usage_total',
    'Metric usage frequency',
    ['metric_name'],  # GMV/DAU/营收/转化率等
    registry=registry
)

# 缓存命中率
cache_hit_rate = Gauge(
    'chatbi_cache_hit_rate',
    'Cache hit rate',
    ['cache_type'],  # redis/memory
    registry=registry
)

# LLM调用统计
llm_requests = Counter(
    'chatbi_llm_requests_total',
    'Total LLM API requests',
    ['model', 'status'],  # model: glm-4-flash/glm-4-plus, status: success/error
    registry=registry
)

llm_tokens = Counter(
    'chatbi_llm_tokens_total',
    'Total LLM tokens consumed',
    ['model', 'type'],  # type: prompt/completion
    registry=registry
)


# ============================================
# 应用信息
# ============================================

# 应用版本信息
app_info = Info(
    'chatbi_app',
    'chatBI application information',
    registry=registry
)

# 设置应用信息
app_info.info({
    'version': '2.0.0',
    'build': 'production',
    'environment': os.getenv('ENV', 'development')
})


# ============================================
# 辅助函数
# ============================================

def track_query(query_type: str, status: str = 'success'):
    """记录查询指标."""
    query_counter.labels(status=status, query_type=query_type).inc()


def track_query_duration(query_type: str, duration: float):
    """记录查询延迟."""
    query_duration.labels(query_type=query_type).observe(duration)


def track_intent_recognition(layer: str, success: bool, duration: float):
    """记录意图识别指标."""
    intent_recognition_counter.labels(layer=layer, success=str(success).lower()).inc()
    intent_recognition_duration.labels(layer=layer).observe(duration)


def track_db_query(operation: str, table: str, duration: float):
    """记录数据库查询指标."""
    db_query_counter.labels(operation=operation, table=table).inc()
    db_query_duration.labels(operation=operation, table=table).observe(duration)


def track_metric_usage(metric_name: str):
    """记录指标使用频率."""
    metric_usage.labels(metric_name=metric_name).inc()


def track_llm_request(model: str, status: str, prompt_tokens: int = 0, completion_tokens: int = 0):
    """记录LLM调用."""
    llm_requests.labels(model=model, status=status).inc()
    if prompt_tokens > 0:
        llm_tokens.labels(model=model, type='prompt').inc(prompt_tokens)
    if completion_tokens > 0:
        llm_tokens.labels(model=model, type='completion').inc(completion_tokens)


if __name__ == "__main__":
    """测试指标导出."""
    from prometheus_client import generate_latest
    
    # 生成一些测试数据
    track_query('simple', 'success')
    track_query_duration('simple', 0.25)
    track_intent_recognition('l1', True, 0.005)
    track_db_query('select', 'fact_orders', 0.1)
    track_metric_usage('GMV')
    track_llm_request('glm-4-flash', 'success', 100, 50)
    
    # 导出指标
    metrics = generate_latest(registry)
    print(metrics.decode('utf-8'))
EOF