
import sys
import os
from datetime import datetime

# Add project root
sys.path.append(os.getcwd())

from src.inference.intent import QueryIntent, TimeGranularity
from src.mql.federated_query import QueryRouter, DataSource

def test_federated_routing():
    print("🧪 Testing Federated Query Routing...")
    
    router = QueryRouter()
    
    # Test Case 1: Analytical Query
    intent1 = QueryIntent(
        query="Show GMV last month",
        core_query="GMV",
        time_range=None,
        time_granularity=TimeGranularity.MONTH,
        aggregation_type=None,
        dimensions=[],
        comparison_type=None,
        filters={},
        trend_type=None,
        sort_requirement=None,
        threshold_filters=[]
    )
    plan1 = router.get_execution_plan(intent1)
    print(f"Query: '{intent1.query}' -> Source: {plan1['source']}")
    assert plan1['source'] == DataSource.ANALYTICAL.value
    
    # Test Case 2: Real-time Query
    intent2 = QueryIntent(
        query="Show current inventory",
        core_query="inventory",
        time_range=None,
        time_granularity=None,
        aggregation_type=None,
        dimensions=[],
        comparison_type=None,
        filters={},
        trend_type=None,
        sort_requirement=None,
        threshold_filters=[]
    )
    plan2 = router.get_execution_plan(intent2)
    print(f"Query: '{intent2.query}' -> Source: {plan2['source']}")
    assert plan2['source'] == DataSource.REALTIME.value
    
    # Test Case 3: Real-time via Chinese keyword
    intent3 = QueryIntent(
        query="实时销售额",
        core_query="销售额",
        time_range=None,
        time_granularity=None,
        aggregation_type=None,
        dimensions=[],
        comparison_type=None,
        filters={},
        trend_type=None,
        sort_requirement=None,
        threshold_filters=[]
    )
    plan3 = router.get_execution_plan(intent3)
    print(f"Query: '{intent3.query}' -> Source: {plan3['source']}")
    assert plan3['source'] == DataSource.REALTIME.value
    
    print("\n✅ Test Passed: Federation logic works!")

if __name__ == "__main__":
    test_federated_routing()
