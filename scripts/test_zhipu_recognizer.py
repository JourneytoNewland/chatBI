
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.inference.zhipu_intent import ZhipuIntentRecognizer

def test_zhipu():
    print("🚀 Testing ZhipuAI Intent Recognizer...")
    
    # 1. Initialize
    try:
        recognizer = ZhipuIntentRecognizer(model="glm-4-flash")
        print("✅ Recognizer initialized")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False

    # 2. Test Queries
    test_queries = [
        "最近7天的GMV",
        "本月按渠道统计DAU",
        "电商订单量同比增长",
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        try:
            result = recognizer.recognize(query)
            
            if result:
                print(f"   ✅ core_query: {result.core_query}")
                print(f"   📊 time_range: {result.time_range}")
                print(f"   📏 dimensions: {result.dimensions}")
                print(f"   🎯 confidence: {result.confidence}")
                print(f"   ⏱️ latency: {result.latency*1000:.2f}ms")
                print(f"   🔢 tokens: {result.tokens_used.get('total_tokens', 'N/A')}")
            else:
                print("   ❌ Recognition failed (returned None)")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return True

if __name__ == "__main__":
    if not test_zhipu():
        sys.exit(1)
