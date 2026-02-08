import yaml
import os
from typing import List, Dict, Optional, Any
from pydantic import BaseModel

class MetricDefinition(BaseModel):
    id: str
    name: str
    code: str
    description: str
    domain: str
    table: str
    column: str
    unit: Optional[str] = None
    synonyms: List[str] = []
    formula: Optional[str] = None

class MetricLoader:
    _instance = None
    _metrics: List[MetricDefinition] = []
    _metric_map: Dict[str, MetricDefinition] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MetricLoader, cls).__new__(cls)
            cls._instance._load_metrics()
        return cls._instance

    def _load_metrics(self):
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "configs", "metrics.yaml")
        if not os.path.exists(config_path):
            print(f"⚠️ Warning: Metric config not found at {config_path}")
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data and "metrics" in data:
                    self._metrics = [MetricDefinition(**m) for m in data["metrics"]]
                    self._build_map()
                    print(f"✅ Loaded {len(self._metrics)} metrics from config")
        except Exception as e:
            print(f"❌ Error loading metrics: {e}")

    def _build_map(self):
        self._metric_map = {}
        for m in self._metrics:
            # Map by name and code
            self._metric_map[m.name.lower()] = m
            self._metric_map[m.code.lower()] = m
            # Map by synonyms
            for syn in m.synonyms:
                self._metric_map[syn.lower()] = m

    def get_all_metrics(self) -> List[Dict[str, Any]]:
        return [m.model_dump() for m in self._metrics]

    def get_metric(self, name: str) -> Optional[MetricDefinition]:
        return self._metric_map.get(name.lower())

# Global instance
metric_loader = MetricLoader()
