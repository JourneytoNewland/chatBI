"""快速初始化Qdrant数据."""

from src.recall.vector.qdrant_store import QdrantVectorStore, QdrantConfig
from src.recall.vector.vectorizer import MetricVectorizer
from src.recall.vector.models import MetricMetadata

# 初始化
config = QdrantConfig()
store = QdrantVectorStore(config)
vectorizer = MetricVectorizer(model_name="BAAI/bge-m3")

# 测试数据
test_metrics = [
    {"id": 1, "name": "GMV", "code": "gmv", "description": "成交总额，即所有订单的金额总和", "synonyms": ["成交总额", "交易额", "销售额", "总销售额"], "domain": "电商"},
    {"id": 2, "name": "DAU", "code": "dau", "description": "日活跃用户数，当日有登录或使用行为的用户数量", "synonyms": ["日活", "日活跃用户", "活跃用户数"], "domain": "用户"},
    {"id": 3, "name": "转化率", "code": "conversion_rate", "description": "用户转化率，从访问到下单的转化比例", "synonyms": ["转化率", "转化", "下单转化率"], "domain": "运营"},
    {"id": 4, "name": "客单价", "code": "avg_order_value", "description": "平均订单金额，用户平均每单的消费金额", "synonyms": ["客单价", "人均消费", "平均订单金额"], "domain": "电商"},
    {"id": 5, "name": "留存率", "code": "retention_rate", "description": "用户留存率，新用户在后续时间段继续使用的比例", "synonyms": ["留存率", "留存", "用户留存"], "domain": "用户"},
    {"id": 6, "name": "营收", "code": "revenue", "description": "实际营业收入", "synonyms": ["收入", "营业收入"], "domain": "财务"},
    {"id": 7, "name": "毛利率", "code": "gross_margin", "description": "毛利润与销售额的比率", "synonyms": ["毛利率", "毛利"], "domain": "财务"},
    {"id": 8, "name": "复购率", "code": "repurchase_rate", "description": "用户重复购买的比例", "synonyms": ["复购率", "重复购买"], "domain": "用户"},
    {"id": 9, "name": "订单量", "code": "order_count", "description": "订单总数", "synonyms": ["订单数", "订单总量"], "domain": "电商"},
    {"id": 10, "name": "增长率", "code": "growth_rate", "description": "同比增长率", "synonyms": ["增长", "同比"], "domain": "财务"},
]

print(f"开始向量化 {len(test_metrics)} 个指标...")
vectors = []
for metric in test_metrics:
    metadata = MetricMetadata(
        name=metric["name"],
        code=metric["code"],
        description=metric["description"],
        synonyms=metric["synonyms"],
        domain=metric["domain"],
    )
    vec = vectorizer.vectorize(metadata)
    vectors.append(vec)
    print(f"  ✓ {metric['name']}: {vec.shape}")

print("\n开始存储到 Qdrant...")
client = store.connect()
batch_size = 10

from qdrant_client.models import PointStruct
points = [
    PointStruct(
        id=metric["id"],
        vector=vector.tolist(),
        payload={
            "metric_id": str(metric["id"]),
            "metric_name": metric["name"],
            "metric_code": metric["code"],
            "description": metric["description"],
            "domain": metric["domain"],
            "synonyms": metric["synonyms"],
        }
    )
    for metric, vector in zip(test_metrics, vectors)
]

client.upsert(
    collection_name=config.collection_name,
    points=points
)

print(f"\n✅ 成功存储 {len(points)} 条数据到 Qdrant")
print(f"   向量维度: {vectors[0].shape[0]}")
