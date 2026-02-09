from typing import Dict, Optional, List, Any
import uuid
from .models import SessionContext, TurnContext

class ContextManager:
    _instance = None
    _store: Dict[str, SessionContext] = {}  # In-memory store given MVP requirement

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ContextManager, cls).__new__(cls)
        return cls._instance

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self._store[session_id] = SessionContext(session_id=session_id)
        return session_id

    def get_session(self, session_id: str) -> Optional[SessionContext]:
        return self._store.get(session_id)

    def resolve_context(self, session_id: str, current_intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merges current intent with session history.
        
        Logic:
        1. If session doesn't exist, return current intent as is.
        2. If current intent has NO metric but HAS dimensions (Drill-down), inherit metric from last turn.
        3. If current intent has NO metric and NO dimensions but HAS filters (Filter-update), inherit metric.
        4. Time ranges in current intent override history.
        """
        session = self.get_session(session_id)
        if not session or not session.get_last_turn():
            return current_intent

        last_turn = session.get_last_turn()
        merged_intent = current_intent.copy()

        # Check for Drill-down (No metric in current, but valid dimensions/filters)
        current_metric = current_intent.get('metric')
        current_dims = current_intent.get('dimensions', [])
        
        # Scenario: "按地区拆解" (Drill-down) -> Inherit Metric & Time
        if not current_metric and last_turn.metric:
            print(f"🧠 [ContextManager] Detected Drill-down/Follow-up. Inheriting metric: {last_turn.metric['name']}")
            merged_intent['metric'] = last_turn.metric
            
            # Inherit filters (e.g. time_range) if not overridden
            # We assume current intent might have sparse filters
            current_filters = current_intent.get('filters', {})
            inherited_filters = last_turn.filters.copy()
            
            # Merge logic: New filters override old ones
            inherited_filters.update(current_filters)
            merged_intent['filters'] = inherited_filters
            
            # Dimensions are usually additive or replacement based on intent
            # For now, if user says "by region", we set dimensions to ['region']
            # If user didn't specify dimension, we might keep old ones? Usually no, unless explicit.
            # But here we stick to: current dimensions override unless empty?
            # Actually for "按地区", dimensions are ['region']. "和昨天比" (compare), dimensions might be empty.
            if not current_dims and last_turn.dimensions:
                 # If follow-up is just filter change ("look at last 30 days"), keep dimensions?
                 # It's safer to inherit dimensions IF the query is purely a filter update.
                 # But distinguishing "drill-down" vs "filter-update" vs "new query" is key.
                 # Heuristic: If we inherited metric, we should probably inherit dimensions unless overrides provided.
                 # But "Drill-down" usually MEANS changing dimensions.
                 pass

        return merged_intent

    def save_turn(self, session_id: str, turn_data: Dict[str, Any]):
        session = self.get_session(session_id)
        if session:
            turn = TurnContext(
                turn_id=str(uuid.uuid4()),
                query=turn_data.get('query', ''),
                intent_type=turn_data.get('intent_type', 'UNKNOWN'),
                metric=turn_data.get('metric'),
                dimensions=turn_data.get('dimensions', []),
                filters=turn_data.get('filters', {}),
                sql_generated=turn_data.get('sql')
            )
            session.add_turn(turn)
