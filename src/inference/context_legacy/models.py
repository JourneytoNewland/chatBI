from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
import time

class TurnContext(BaseModel):
    """Represents a single turn in the conversation."""
    turn_id: str
    query: str
    intent_type: str  # e.g., 'QUERY_METRIC', 'DRILL_DOWN', 'FILTER_UPDATE'
    metric: Optional[Dict[str, Any]] = None # The primary metric entity
    dimensions: List[str] = []
    filters: Dict[str, Any] = {} # e.g., {'time_range': '7d', 'region': 'East'}
    sql_generated: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)

class SessionContext(BaseModel):
    """Represents the entire session state."""
    session_id: str
    created_at: float = Field(default_factory=time.time)
    last_updated: float = Field(default_factory=time.time)
    turns: List[TurnContext] = []

    def add_turn(self, turn: TurnContext):
        self.turns.append(turn)
        self.last_updated = time.time()
        # Keep only last 10 turns
        if len(self.turns) > 10:
            self.turns.pop(0)

    def get_last_turn(self) -> Optional[TurnContext]:
        return self.turns[-1] if self.turns else None
