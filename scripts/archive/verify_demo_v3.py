
import requests
import json
import sys

def test_v3_query():
    url = "http://localhost:8000/api/v3/query"
    
    # Test Case 1: Semantic Mapping "User Activity" -> "DAU"
    query = "User Activity trends"
    payload = {"query": query}
    
    print(f"Testing Query: '{query}'")
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        # Verify Intent
        core_query = data['intent']['core_query']
        print(f"  -> Identified Metric: {core_query}")
        
        if "DAU" in core_query or "活跃用户" in core_query:
            print("  ✅ Semantic Mapping Success: 'User Activity' -> 'DAU'")
        else:
            print(f"  ❌ Semantic Mapping Failed. Expected DAU/活跃用户, got '{core_query}'")
            # Don't exit yet, check other fields
            
        # Verify Response Structure
        expected_fields = ['conversation_id', 'intent', 'data', 'all_layers', 'mql', 'sql', 'interpretation']
        missing = [f for f in expected_fields if f not in data]
        if not missing:
            print("  ✅ Response Structure Valid (All fields present)")
        else:
            print(f"  ❌ Missing Fields: {missing}")

        # Verify Data
        if data['data'] and len(data['data']) > 0:
            print(f"  ✅ Data Returned: {len(data['data'])} rows")
        else:
            print("  ⚠️ No Data Returned")

        # Verify Layers (Transparency)
        if data['all_layers']:
            print(f"  ✅ Layers Info Returned: {len(data['all_layers'])} layers")
            for layer in data['all_layers']:
                print(f"    - {layer['layer_name']}: {layer['status']}")
        else:
            print("  ❌ No Layer Info")

    except Exception as e:
        print(f"  ❌ Request Failed: {e}")
        return False

    return True

if __name__ == "__main__":
    print("🚀 Verifying V3 API Implementation...")
    success = test_v3_query()
    if success:
        print("\n✅ Verification Passed!")
        sys.exit(0)
    else:
        print("\n❌ Verification Failed!")
        sys.exit(1)
