
import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v3/query"

def test_query(query, expected_metric):
    print(f"\n🔍 Testing Query: '{query}'")
    payload = {"query": query}
    try:
        response = requests.post(BASE_URL, json=payload)
        if response.status_code == 200:
            data = response.json()
            metric_name = data['intent']['core_query']
            source_layer = data['intent']['source_layer']
            confidence = data['intent']['confidence']
            
            print(f"   ✅ Metric: {metric_name} (Expected: {expected_metric})")
            print(f"   📊 Source: {source_layer}")
            print(f"   🎯 Confidence: {confidence}")
            
            # Check L2 metadata for match type
            for layer in data['all_layers']:
                if "L2" in layer['layer_name']:
                    candidates = layer['metadata'].get('candidates', [])
                    if candidates:
                        print(f"   ℹ️ L2 Match: {candidates[0]['source']} (Score: {candidates[0]['final_score']:.4f})")
                    else:
                        print("   ℹ️ L2 Match: None")
            
            if expected_metric.lower() in metric_name.lower():
                print("   🎉 Result: PASS")
            else:
                print("   ⚠️ Result: MISMATCH")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Connection Error: {e}")

if __name__ == "__main__":
    # Give server a moment to reload
    print("Waiting for server reload...")
    time.sleep(2)
    
    # Test cases unlikely to be in hardcoded map
    test_query("how much did we sell", "GMV")
    test_query("money made", "Revenue") # Or GMV
    test_query("users online", "DAU")
