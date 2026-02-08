#!/usr/bin/env python3
"""测试 SQL 生成逻辑."""
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mql.sql_generator_v2 import SQLGeneratorV2
from src.inference.intent import QueryIntent, TimeGranularity, AggregationType

def test_sql_generation():
    """测试 SQL 生成器."""
    print("🧪 Testing SQL Generation Logic...")
    print("=" * 60)
    
    # 初始化生成器 (不需要真实数据库连接)
    try:
        generator = SQLGeneratorV2()
        print("✅ SQLGeneratorV2 initialized\n")
    except Exception as e:
        print(f"⚠️ Warning: {e}")
        print("   Continuing with SQL generation test...\n")
        generator = SQLGeneratorV2()
    
    # 测试用例
    test_cases = [
        {
            "name": "简单查询: GMV",
            "intent": QueryIntent(
                core_query="GMV",
                time_range=(datetime.now() - timedelta(days=7), datetime.now()),
                time_granularity=TimeGranularity.DAY,
                aggregation_type=AggregationType.SUM,
                dimensions=[],
                filters={}
            )
        },
        {
            "name": "按维度查询: 按渠道统计DAU",
            "intent": QueryIntent(
                core_query="DAU",
                time_range=(datetime.now() - timedelta(days=30), datetime.now()),
                time_granularity=TimeGranularity.DAY,
                aggregation_type=AggregationType.AVG,
                dimensions=["渠道"],
                filters={}
            )
        },
        {
            "name": "多维度查询: 按地区和品类统计订单量",
            "intent": QueryIntent(
                core_query="订单量",
                time_range=(datetime.now() - timedelta(days=7), datetime.now()),
                time_granularity=TimeGranularity.DAY,
                aggregation_type=AggregationType.COUNT,
                dimensions=["地区", "品类"],
                filters={}
            )
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test Case {i}: {test_case['name']}")
        print(f"{'='*60}")
        
        try:
            sql, params = generator.generate(test_case['intent'])
            
            print(f"\n📝 Generated SQL:")
            print("-" * 60)
            print(sql)
            print("-" * 60)
            
            if params:
                print(f"\n🔢 Parameters:")
                for key, value in params.items():
                    print(f"   {key}: {value}")
            
            print(f"\n✅ SQL generation successful")
            
        except Exception as e:
            print(f"\n❌ SQL generation failed: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("🎉 SQL Generation Test Complete")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    test_sql_generation()
