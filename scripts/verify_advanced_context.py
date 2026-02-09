import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v3/query"

def run_query(query, session_id=None):
    payload = {"query": query, "top_k": 5}
    if session_id:
        payload["conversation_id"] = session_id
    
    resp = requests.post(BASE_URL, json=payload)
    if resp.status_code != 200:
        print(f"❌ Error: {resp.text}")
        sys.exit(1)
    return resp.json()

def test_time_override():
    print("\n🧪 Test Case 1: Time Override (Last 7d -> Last 30d)")
    
    # Turn 1
    r1 = run_query("最近7天的GMV")
    sid = r1["conversation_id"]
    print(f"Turn 1 Intent: {r1['intent']['core_query']} | Time: {r1['intent']['filters'].get('time_range')}")
    
    # Turn 2: Override time
    r2 = run_query("那最近30天的呢", sid)
    intent = r2['intent']
    print(f"Turn 2 Intent: {intent['core_query']} | Time: {intent['filters'].get('time_range')}")
    
    if "GMV" in intent['core_query'] and intent['filters'].get('time_range') != r1['intent']['filters'].get('time_range'):
        print("✅ Success: Metric Inherited, Time Overridden")
    else:
        print("❌ Failure: Time override failed")

def test_metric_switch_keep_context():
    print("\n🧪 Test Case 2: Metric Switch (GMV -> Profit, keep filters)")
    
    # Turn 1: GMV in East Region
    r1 = run_query("华东地区的GMV")
    sid = r1["conversation_id"]
    print(f"Turn 1 Intent: {r1['intent']['core_query']} | Dims: {r1['intent']['dimensions']}")
    
    # Turn 2: Switch to Profit (expect to keep Region?)
    # Note: Current simple ContextManager might not support "keep dimensions on new metric" unless explicitly designed.
    # Our current logic: resolve_context returns merged intent.
    # If user says "What about Profit?", intent has Metric=Profit.
    # Logic rule 3 says: IF intent has metric, we usually DON'T inherit unless specific rules apply.
    # Let's see behavior.
    r2 = run_query("那利润呢", sid)
    intent = r2['intent']
    print(f"Turn 2 Intent: {intent['core_query']} | Dims: {intent['dimensions']}")
    
    # Current implementation might NOT inherit dimensions if metric changes. This is a design choice.
    # If we want it to, we need to update ContextManager. For now, let's just observe.

if __name__ == "__main__":
    test_time_override()
    test_metric_switch_keep_context()
