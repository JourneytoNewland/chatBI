import urllib.request
import urllib.parse
import json
import time

BASE_URL = "http://localhost:8000"

def test_query(query, expected_metric=None):
    print(f"\n🔍 Testing Query: '{query}'")
    url = f"{BASE_URL}/api/v1/search"
    payload = {
        "query": query,
        "top_k": 5
    }
    data = json.dumps(payload).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        start_time = time.time()
        with urllib.request.urlopen(req) as response:
            body = response.read().decode('utf-8')
            end_time = time.time()
            
            if response.status == 200:
                print(f"✅ Success ({response.status}) - {end_time - start_time:.4f}s")
                try:
                    res_json = json.loads(body)
                except json.JSONDecodeError:
                    print(f"❌ Failed to decode JSON response: {body}")
                    return

                if expected_metric:
                    candidates = res_json.get("candidates", [])
                    found = any(c["name"] == expected_metric for c in candidates)
                    if found:
                        print(f"   [PASS] Found expected metric: {expected_metric}")
                    else:
                        print(f"   [FAIL] Expected metric '{expected_metric}' not found in top results")
                
                if res_json.get("intent"):
                    intent = res_json["intent"]
                    print(f"   Intent: {intent.get('core_query')}")
                    if intent.get("time_range"):
                        print(f"   Time Range: {intent.get('time_range')}")
                    if intent.get("dimensions"):
                        print(f"   Dimensions: {intent.get('dimensions')}")
            else:
                print(f"❌ Failed ({response.status}): {body}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def main():
    print("Waiting for server to start...")
    # Simple check loop
    for _ in range(10):
        try:
            with urllib.request.urlopen(f"{BASE_URL}/health") as response:
                if response.status == 200:
                    print("Server is up!")
                    break
        except:
            time.sleep(1)
    else:
        print("Server failed to start.")
        return

    test_query("GMV", "GMV")
    test_query("最近7天成交金额", "GMV")
    test_query("DAU", "DAU")
    test_query("按地区统计用户活跃度", "DAU")
    test_query("为什么转化率下降了？", "转化率")

if __name__ == "__main__":
    main()
