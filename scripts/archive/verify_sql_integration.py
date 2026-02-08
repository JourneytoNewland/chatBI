import requests
import json

BASE_URL = "http://localhost:8000/api/v3/query"

def test_sql_generation_integration():
    print("🧪 Testing SQL Generation Integration...")
    
    test_queries = [
        "最近7天的GMV",
        "本月按渠道统计DAU",
        "按地区的订单量"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: '{query}'")
        print(f"{'='*60}")
        
        try:
            response = requests.post(BASE_URL, json={"query": query})
            if response.status_code == 200:
                data = response.json()
                
                # Check for SQL in metadata
                metadata = data.get('metadata', {})
                generated_sql = metadata.get('generated_sql', 'N/A')
                sql_params = metadata.get('sql_params', {})
                
                print(f"\n📊 Intent: {data['intent']['core_query']}")
                print(f"📏 Dimensions: {data['intent']['dimensions']}")
                
                if generated_sql and generated_sql != "SQL generation disabled or failed":
                    print(f"\n✅ SQL Generated:")
                    print("-" * 60)
                    # Pretty print SQL
                    print(generated_sql)
                    print("-" * 60)
                    if sql_params:
                        print(f"\n🔢 Parameters: {sql_params}")
                else:
                    print(f"\n⚠️ SQL: {generated_sql}")
                    
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"❌ Request failed: {e}")
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    import time
    print("Waiting for server...")
    time.sleep(2)
    test_sql_generation_integration()
