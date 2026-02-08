
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.recall.graph.graph_store import GraphStore
from src.config.metric_loader import metric_loader

def ingest_graph_data():
    """将指标数据加载到 Neo4j."""
    print("🚀 Starting Metric Ingestion to Neo4j...")
    
    # 1. 加载指标配置
    metrics_metadata = metric_loader.get_all_metrics()
    print(f"📦 Loaded {len(metrics_metadata)} metrics from config.")
    
    # 2. 初始化 GraphStore
    store = GraphStore()
    
    try:
        # 3. 创建索引
        print("🔧 Creating constraints and indexes...")
        store.create_constraints()
        
        # 4. 写入数据
        print("🔄 Ingesting metrics...")
        for metric in metrics_metadata:
            store.upsert_metric(metric)
            print(f"   - Ingested: {metric['name']} ({metric['code']})")
        
        print(f"✅ Successfully ingested {len(metrics_metadata)} metrics into Neo4j.")
        
    except Exception as e:
        print(f"❌ Ingestion failed: {e}")
    finally:
        store.close()

if __name__ == "__main__":
    ingest_graph_data()
