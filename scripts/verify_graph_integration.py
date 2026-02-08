
import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v3/query"

def test_query(query, expected_domain_hit=True):
    print(f"\n🔍 Testing Graph Query: '{query}'")
    payload = {"query": query}
    try:
        response = requests.post(BASE_URL, json=payload)
        if response.status_code == 200:
            data = response.json()
            metric_name = data['intent']['core_query']
            source_layer = data['intent']['source_layer']
            confidence = data['intent']['confidence']
            
            print(f"   Metric: {metric_name}")
            print(f"   Source: {source_layer}")
            print(f"   Confidence: {confidence}")
            
            # Check L2 metadata for graph candidates
            found_graph_candidates = False
            for layer in data['all_layers']:
                if "L2" in layer['layer_name']:
                    metadata = layer['metadata']
                    graph_candidates = metadata.get('graph_candidates', [])
                    if graph_candidates:
                        print(f"   🕸️ Graph Candidates Found: {graph_candidates}")
                        found_graph_candidates = True
                    else:
                        print("   🕸️ Graph Candidates: None")
            
            if expected_domain_hit and found_graph_candidates:
                print("   🎉 Result: PASS (Graph Recall Triggered)")
            elif not expected_domain_hit and not found_graph_candidates:
                print("   🎉 Result: PASS (No Graph Recall as expected)")
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
    
    # Test cases
    test_query("电商指标有哪些") # Should hit '电商' domain
    test_query("用户增长情况")   # Should hit '用户' domain
    test_query("普通的查询")       # Should NOT hit domain
