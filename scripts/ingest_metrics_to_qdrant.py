
import sys
import os
from typing import List

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import settings
from src.config import metric_loader
from src.recall.vector.qdrant_store import QdrantVectorStore
from src.recall.vector.vectorizer import MetricVectorizer
from src.recall.vector.models import MetricMetadata

def ingest_metrics():
    print("🚀 Starting Metric Ingestion to Qdrant...")
    
    # 1. Load Metrics
    raw_metrics = metric_loader.get_all_metrics()
    print(f"📦 Loaded {len(raw_metrics)} metrics from config.")
    
    # 2. Convert to MetricMetadata objects
    metric_objects = []
    for m in raw_metrics:
        try:
            metadata = MetricMetadata(
                name=m['name'],
                code=m['code'],
                description=m['description'],
                synonyms=m.get('synonyms', []),
                domain=m['domain'],
                formula=m.get('formula')
            )
            metric_objects.append(metadata)
        except Exception as e:
            print(f"⚠️ Skipping invalid metric {m.get('name')}: {e}")
            
    # 3. Initialize Vector Components
    try:
        store = QdrantVectorStore()
        # Verify connection
        client = store.connect()
        collection_info = client.get_collections()
        print(f"✅ Connected to Qdrant at {settings.qdrant.host}:{settings.qdrant.port}")
    except Exception as e:
        print(f"❌ Failed to connect to Qdrant: {e}")
        print("Please ensure Qdrant is running (e.g., via Docker).")
        return

    vectorizer = MetricVectorizer()
    print(f"🧠 Initialized Vectorizer ({vectorizer.model_name})")

    # 4. Create Collection
    store.create_collection(vector_size=vectorizer.embedding_dim, recreate=True)
    print("✨ Created collection 'metrics'")

    # 5. Vectorize and Upsert
    print("🔄 Vectorizing metrics (this may take a moment)...")
    vectors = vectorizer.vectorize_batch(metric_objects)
    
    ids = [m.code for m in metric_objects]
    payloads = [m.model_dump() for m in metric_objects] # Use model_dump for Pydantic v2
    
    count = store.upsert(ids, vectors, payloads)
    print(f"✅ Successfully ingested {count} metrics into Qdrant.")

if __name__ == "__main__":
    ingest_metrics()
