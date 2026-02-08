#!/usr/bin/env python3
"""Quick test for L1 matching logic"""

query = "本月按渠道统计DAU"
query_lower = query.lower()

# Test metric: DAU
metric_name_lower = "dau"

print(f"Query: '{query}'")
print(f"Query Lower: '{query_lower}'")
print(f"Metric: '{metric_name_lower}'")
print(f"Metric in Query: {metric_name_lower in query_lower}")

if metric_name_lower in query_lower:
    idx = query_lower.find(metric_name_lower)
    print(f"Index: {idx}")
    print(f"Char before ({idx-1}): '{query_lower[idx-1] if idx > 0 else 'START'}'")
    print(f"Char after ({idx+len(metric_name_lower)}): '{query_lower[idx+len(metric_name_lower)] if idx+len(metric_name_lower) < len(query_lower) else 'END'}'")
    
    is_word = (idx == 0 or not query_lower[idx-1].isalnum()) and \
              (idx + len(metric_name_lower) == len(query_lower) or \
               not query_lower[idx + len(metric_name_lower)].isalnum())
    
    print(f"Is Word: {is_word}")
    
    # Check isalnum for Chinese characters
    print(f"\nChinese char '计' isalnum: {'计'.isalnum()}")
    print(f"Chinese char '统' isalnum: {'统'.isalnum()}")
