import requests
import json

BASE_URL = "http://localhost:8000/api/v3/query"

def test_drill_down():
    print("🧪 Testing Multi-turn Drill-down...")
    
    # Turn 1: GMV last 7 days
    payload1 = {
        "query": "最近7天的GMV",
        "top_k": 5
    }
    resp1 = requests.post(BASE_URL, json=payload1).json()
    session_id = resp1.get("conversation_id")
    print(f"Turn 1 Session ID: {session_id}")
    print(f"Turn 1 Intent: {resp1['intent']}")
    
    assert "GMV" in resp1['intent']['core_query']
    
    # Turn 2: By Region (Drill-down)
    payload2 = {
        "query": "按地区拆解",
        "conversation_id": session_id,
        "top_k": 5
    }
    resp2 = requests.post(BASE_URL, json=payload2).json()
    print(f"Turn 2 Intent: {resp2['intent']}")
    
    # Verify inheritance
    intent2 = resp2['intent']
    # Check if metric "GMV" is inherited (core_query should reflect metric name)
    # Note: Our logic might set core_query to metric name if inherited
    if "GMV" in intent2['core_query']:
        print("✅ Metric Inherited: GMV")
    else:
        print(f"❌ Metric NOT Inherited. Got: {intent2['core_query']}")
        
    # Check dimensions
    if "region" in intent2['dimensions'] or "地区" in str(intent2['dimensions']):
        print("✅ Dimension Added: Region")
    else:
         print(f"❌ Dimension NOT Added. Got: {intent2['dimensions']}")

if __name__ == "__main__":
    try:
        test_drill_down()
    except Exception as e:
        print(f"Test Failed: {e}")
