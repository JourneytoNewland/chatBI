
from enum import Enum
from typing import Optional
from src.inference.intent import QueryIntent

class DataSource(Enum):
    REALTIME = "realtime"  # Redis / ClickHouse Realtime
    ANALYTICAL = "analytical"  # PostgreSQL / Doris / Hive
    SEARCH = "search"  # Elasticsearch / Vector DB

class QueryRouter:
    """Query Router for Federated Querying."""
    
    def __init__(self):
        pass

    def route_query(self, intent: QueryIntent) -> DataSource:
        """Route the query to the appropriate data source based on intent."""
        
        # 1. Check for Real-time triggers
        # Keywords in query or specific time granularity
        realtime_keywords = ["now", "current", "realtime", "实时", "当前", "现在"]
        query_text = intent.query.lower()
        
        if any(kw in query_text for kw in realtime_keywords):
            return DataSource.REALTIME
            
        # 2. Check for Search triggers (unstructured)
        # If intent has no core metric and no aggregation, maybe it's just a document search? 
        # (This logic can be refined)
        
        # 3. Default to Analytical
        return DataSource.ANALYTICAL

    def get_execution_plan(self, intent: QueryIntent) -> dict:
        """Generate an execution plan."""
        source = self.route_query(intent)
        
        plan = {
            "source": source.value,
            "reason": "Default routing",
            "suggested_engine": "Unknown"
        }
        
        if source == DataSource.REALTIME:
            plan["reason"] = "Detected real-time intent"
            plan["suggested_engine"] = "Redis/ClickHouse"
        elif source == DataSource.ANALYTICAL:
            plan["reason"] = "Standard analytical query"
            plan["suggested_engine"] = "PostgreSQL"
            
        return plan
