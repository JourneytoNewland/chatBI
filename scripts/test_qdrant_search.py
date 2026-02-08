
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.recall.vector.qdrant_store import QdrantVectorStore
from src.recall.vector.vectorizer import MetricVectorizer
from src.config.settings import settings

def test_search():
    print("🚀 Testing Qdrant Search...")
    
    # 1. Initialize
    try:
        store = QdrantVectorStore()
        vectorizer = MetricVectorizer()
        print(f"✅ Initialized Store & Vectorizer ({vectorizer.model_name})")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return

    # 2. Test Queries
    queries = ["sales", "user activity", "how much money", "revenue"]
    
    for q in queries:
        print(f"\n🔍 Searching for: '{q}'")
        try:
            # Vectorize query
            vec = vectorizer.model.encode(q, normalize_embeddings=True)
            
            # Search
            results = store.search(vec, top_k=3)
            
            for rank, res in enumerate(results, 1):
                payload = res['payload']
                print(f"   {rank}. {payload['name']} ({payload['code']}) - Score: {res['score']:.4f}")
                
        except Exception as e:
            print(f"   ❌ Search failed: {e}")

if __name__ == "__main__":
    test_search()
