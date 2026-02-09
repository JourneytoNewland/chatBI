
import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

class ProphetEngine:
    """
    Lightweight Forecasting Engine.
    
    If 'prophet' library is available, use it.
    Otherwise, fall back to a simple Linear Regression + Seasonality model.
    """
    
    def __init__(self):
        self.use_prophet = False
        try:
            from prophet import Prophet
            self.use_prophet = True
        except ImportError:
            print("⚠️ Prophet library not found. Using lightweight fallback model.")

    def forecast(self, data: List[Dict[str, Any]], periods: int = 7) -> List[Dict[str, Any]]:
        """
        Generate forecast.
        
        Args:
            data: List of dicts with 'ds' (date string or datetime) and 'y' (value).
            periods: Number of periods to forecast.
            
        Returns:
            List of dicts with 'ds', 'yhat' (forecast), 'yhat_lower', 'yhat_upper'.
        """
        if not data:
            return []

        # Preprocess data
        processed_data = []
        for row in data:
            ds = row['ds']
            if isinstance(ds, str):
                try:
                    ds = datetime.strptime(ds, "%Y-%m-%d")
                except ValueError:
                    ds = datetime.strptime(ds, "%Y-%m-%d %H:%M:%S")
            processed_data.append({'ds': ds, 'y': float(row['y'])})
            
        processed_data.sort(key=lambda x: x['ds'])

        if self.use_prophet:
            return self._forecast_prophet(processed_data, periods)
        else:
            return self._forecast_lightweight(processed_data, periods)

    def _forecast_prophet(self, data, periods):
        import pandas as pd
        from prophet import Prophet
        
        df = pd.DataFrame(data)
        m = Prophet()
        m.fit(df)
        future = m.make_future_dataframe(periods=periods)
        forecast = m.predict(future)
        
        results = []
        for _, row in forecast.tail(periods).iterrows():
            results.append({
                'ds': row['ds'].strftime("%Y-%m-%d"),
                'yhat': row['yhat'],
                'yhat_lower': row['yhat_lower'],
                'yhat_upper': row['yhat_upper']
            })
        return results

    def _forecast_lightweight(self, data, periods):
        """
        Simple Linear Regression + Weekly Seasonality
        """
        n = len(data)
        if n < 2:
            return []
            
        # 1. Linear Regression (Trend)
        # x = days since start, y = value
        start_date = data[0]['ds']
        x = [(d['ds'] - start_date).days for d in data]
        y = [d['y'] for d in data]
        
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi*yi for xi, yi in zip(x, y))
        sum_xx = sum(xi*xi for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x) if (n * sum_xx - sum_x * sum_x) != 0 else 0
        intercept = (sum_y - slope * sum_x) / n
        
        # 2. Weekly Seasonality
        # Calculate average deviation from trend for each day of week
        seasonality = {i: [] for i in range(7)}
        for i, row in enumerate(data):
            # trend value
            trend = slope * x[i] + intercept
            # actual - trend
            diff = y[i] - trend
            weekday = row['ds'].weekday()
            seasonality[weekday].append(diff)
            
        avg_seasonality = {}
        for w in range(7):
            vals = seasonality[w]
            avg_seasonality[w] = sum(vals) / len(vals) if vals else 0
            
        # 3. Forecast
        last_x = x[-1]
        last_date = data[-1]['ds']
        
        forecast_results = []
        for i in range(1, periods + 1):
            future_x = last_x + i
            future_date = last_date + timedelta(days=i)
            
            # Trend
            trend_val = slope * future_x + intercept
            
            # Seasonality
            season_val = avg_seasonality[future_date.weekday()]
            
            yhat = trend_val + season_val
            
            # Simple confidence intervals (fixed 10% for demo)
            yhat_lower = yhat * 0.9
            yhat_upper = yhat * 1.1
            
            forecast_results.append({
                'ds': future_date.strftime("%Y-%m-%d"),
                'yhat': max(0, yhat), # No negative metrics usually
                'yhat_lower': max(0, yhat_lower),
                'yhat_upper': max(0, yhat_upper)
            })
            
        return forecast_results
