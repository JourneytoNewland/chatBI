import unittest
from src.inference.context.manager import ContextManager

class TestContextManager(unittest.TestCase):
    def setUp(self):
        self.cm = ContextManager()
        self.session_id = self.cm.create_session()

    def test_basic_inheritance(self):
        # Turn 1: GMV last 7 days
        turn1 = {
            "query": "GMV last 7 days",
            "metric": {"name": "GMV"},
            "filters": {"time_range": "last_7d"},
            "dimensions": []
        }
        self.cm.save_turn(self.session_id, turn1)
        
        # Turn 2: By region (inherit metric)
        turn2_input = {
            "query": "by region",
            "metric": None,
            "filters": {},
            "dimensions": ["region"]
        }
        resolved = self.cm.resolve_context(self.session_id, turn2_input)
        
        self.assertIsNotNone(resolved.get('metric'))
        self.assertEqual(resolved['metric']['name'], "GMV")
        self.assertEqual(resolved['filters']['time_range'], "last_7d")
        self.assertEqual(resolved['dimensions'], ["region"])

    def test_filter_override(self):
        # Turn 1
        turn1 = {
            "query": "GMV last 7 days",
            "metric": {"name": "GMV"},
            "filters": {"time_range": "last_7d"}
        }
        self.cm.save_turn(self.session_id, turn1)
        
        # Turn 2: Last 30 days (override time)
        turn2_input = {
            "query": "last 30 days",
            "metric": None,
            "filters": {"time_range": "last_30d"}
        }
        resolved = self.cm.resolve_context(self.session_id, turn2_input)
        
        self.assertEqual(resolved['filters']['time_range'], "last_30d")
        self.assertEqual(resolved['metric']['name'], "GMV")

if __name__ == '__main__':
    unittest.main()
