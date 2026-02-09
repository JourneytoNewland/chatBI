
import sys
import os
import asyncio
from typing import Dict, Any

# Add project root
sys.path.append(os.getcwd())

# Mock the necessary components to avoid full server start dependence for unit testing
# Check if src module matches structure
from src.analysis.prophet_engine import ProphetEngine

def test_engine_directly():
    print("🧪 Testing Prophet Engine Logic...")
    engine = ProphetEngine()
    
    # Mock Data (Linear Trend: y = 2x, Seasonality: None)
    data = []
    base_date = datetime(2023, 1, 1)
    for i in range(20):
        data.append({
            "ds": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
            "y": i * 2
        })
        
    forecast = engine.forecast(data, periods=3)
    
    print(f"Input last: {data[-1]}")
    for f in forecast:
        print(f"Forecast: {f['ds']} -> {f['yhat']:.2f}")
        
    # Verify trend continues
    # Last y was 19*2 = 38. Next should be approx 40, 42, 44
    first_forecast = forecast[0]['yhat']
    assert 39 <= first_forecast <= 41, f"Expected approx 40, got {first_forecast}"
    print("✅ Engine Test Passed!")

if __name__ == "__main__":
    from datetime import datetime, timedelta
    test_engine_directly()
