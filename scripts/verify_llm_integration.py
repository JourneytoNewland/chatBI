
import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v3/query"

def test_query(query, expected_dims=None):
    print(f"\n🔍 Testing LLM Query: '{query}'")
    payload = {"query": query}
    try:
        response = requests.post(BASE_URL, json=payload)
        if response.status_code == 200:
            data = response.json()
            metric_name = data['intent']['core_query']
            dimensions = data['intent']['dimensions']
            time_range = data['intent']['time_range']
            
            print(f"   Metric: {metric_name}")
            print(f"   Dimensions: {dimensions}")
            print(f"   Time Range: {time_range}")
            
            # Check L3 metadata
            for layer in data['all_layers']:
                if "L3" in layer['layer_name']:
                    metadata = layer['metadata']
                    print(f"   🧠 LLM Model: {metadata.get('llm_model', 'N/A')}")
                    print(f"   🔢 Tokens: {metadata.get('tokens', 'N/A')}")
                    print(f"   ⏱️ Latency: {layer.get('duration', 'N/A'):.2f}ms")
                    print(f"   🔌 Real LLM: {metadata.get('real_llm', 'N/A')}")
            
            if expected_dims and set(expected_dims) == set(dimensions):
                print("   🎉 Result: PASS (Dimensions Match)")
            elif expected_dims:
                print(f"   ⚠️ Result: MISMATCH (Expected: {expected_dims})")
            else:
                print("   ✅ Result: OK")
                
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Connection Error: {e}")

if __name__ == "__main__":
    # Give server a moment to reload
    print("Waiting for server reload...")
    time.sleep(2)
    
    # Test cases
    test_query("本月按渠道统计DAU", expected_dims=["渠道"])
    test_query("按地区的成交金额同比", expected_dims=["地区"])
    test_query("最近7天的GMV")
