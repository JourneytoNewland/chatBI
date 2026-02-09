
import sys
import os
from datetime import datetime

# Add project root
sys.path.append(os.getcwd())

# Fix import path
try:
    from src.inference.context import ConversationContext
except ImportError:
    # If running from root, src.inference.context might be shadowed if context is a folder?
    # Actually, the error said `from 'src.inference.context' (.../context/__init__.py)`
    # This implies there IS a folder named `context` inside `src/inference/`?
    # Let me check the file structure again. 
    # Wait, the previous view_file showed `src/inference/context.py`.
    # But the error message said `.../context/__init__.py`. 
    # This means there is BOTH a file `context.py` and a folder `context/`.
    # This causes a conflict.
    pass

from src.inference.intent import QueryIntent, TimeGranularity

def test_context_merge():
    print("🧪 Testing Context Merging...")
    
    ctx = ConversationContext(conversation_id="test_001")
    
    # Mock Turn 1: "Show GMV last 7 days"
    intent1 = QueryIntent(
        query="Show GMV last 7 days",
        core_query="GMV",
        time_range=(datetime(2023, 1, 1), datetime(2023, 1, 7)),
        time_granularity=TimeGranularity.DAY,
        aggregation_type=None,
        dimensions=[],
        comparison_type=None,
        filters={},
        trend_type=None,
        sort_requirement=None,
        threshold_filters=[]
    )
    ctx.add_turn(intent1.query, intent1)
    print("✅ Turn 1 added: Base Query")

    # Mock Turn 2: "In Beijing" (Follow-up)
    # Simulator detects "Beijing" as a filter or dimension, but core_query might be empty or valid
    # Here we simulate intent recognizer returning empty core_query for "In Beijing"
    intent2 = QueryIntent(
        query="In Beijing",
        core_query="", # Empty core query
        time_range=None, # No time info
        time_granularity=None,
        aggregation_type=None,
        dimensions=["City"],
        comparison_type=None,
        filters={"city": "Beijing"},
        trend_type=None,
        sort_requirement=None,
        threshold_filters=[]
    )
    
    print(f"\nBefore Merge (Turn 2): Metric='{intent2.core_query}', Time={intent2.time_range}")
    
    # Do Merge
    last = ctx.get_last_intent()
    if last:
        merged = ctx.merge_intent(intent2, last)
        
        print(f"After Merge (Turn 2):  Metric='{merged.core_query}', Time={merged.time_range}, Filters={merged.filters}")
        
        # Assertions
        assert merged.core_query == "GMV", "Failed to inherit Metric"
        assert merged.time_range is not None, "Failed to inherit Time"
        assert merged.filters.get("city") == "Beijing", "Failed to keep new filter"
        
        print("\n✅ Test Passed: Drill-down context inherited correctly!")
    else:
        print("❌ Test Failed: No last intent found")

if __name__ == "__main__":
    test_context_merge()
