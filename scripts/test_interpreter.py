
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from src.mql.intelligent_interpreter import IntelligentInterpreter

def test_interpreter():
    print("Testing IntelligentInterpreter...")
    
    # Check API Key
    api_key = os.getenv("ZHIPUAI_API_KEY")
    if not api_key:
        print("⚠️ ZHIPUAI_API_KEY not found in environment")
        # Try loading from .env if possible, but for now just warn
    else:
        print("✅ ZHIPUAI_API_KEY found")

    interpreter = IntelligentInterpreter()

    # Mock data
    metric_def = {"name": "GMV", "unit": "元", "description": "Gross Merchandise Value"}
    mql_result = {
        "result": [
            {"date": "2024-01-01", "value": 100},
            {"date": "2024-01-02", "value": 120},
            {"date": "2024-01-03", "value": 110},
            {"date": "2024-01-04", "value": 140},
            {"date": "2024-01-05", "value": 160},
        ],
        "row_count": 5
    }

    try:
        result = interpreter.interpret("最近5天GMV", mql_result, metric_def)
        print("\nInterpretation Result:")
        print(f"Summary: {result.summary}")
        print(f"Confidence: {result.confidence}")
        print(f"Key Findings: {result.key_findings}")
        print(f"Insights: {result.insights}")
    except Exception as e:
        print(f"❌ Intepretation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_interpreter()
