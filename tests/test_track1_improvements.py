import json
import os
import tempfile
import unittest

from tools.citizen_ingest_sanitizer import sanitize_and_parse_request
from tools.hotspot_aggregator import aggregate_hotspots
from tools.messaging_webhook_adapter import normalize_webhook
from tools.priority_budget_optimizer import optimize_priority_and_budget
from tools.public_investment_mapper import map_public_investment_scheme
import tools.hotspot_aggregator as hotspot_module


class Track1ImprovementTests(unittest.TestCase):
    def test_sanitizer_removes_contact_identifiers_before_processing(self):
        result = sanitize_and_parse_request(
            "मेरा नाम रमेश है, फोन 9876543210 और आधार 4589-1234-5678 है। कटिहार में पानी नहीं है."
        )
        self.assertNotIn("9876543210", result["sanitized_text"])
        self.assertNotIn("4589-1234-5678", result["sanitized_text"])
        self.assertEqual(result["detected_category"], "Water & Sanitation")

    def test_webhook_adapter_hashes_sender_and_normalizes_channel(self):
        result = normalize_webhook(
            "whatsapp",
            {"entry": [{"changes": [{"value": {"messages": [{
                "id": "wamid.test",
                "from": "919876543210",
                "text": {"body": "Katihar water pipeline broken"},
            }]}}]}]},
        )
        self.assertEqual(result["channel"], "whatsapp_bot")
        self.assertTrue(result["sender_token"].startswith("sha256:"))
        self.assertNotIn("919876543210", json.dumps(result))

    def test_scheme_mapping_is_review_only(self):
        budget = optimize_priority_and_budget("Water & Sanitation", 0.428, 0.476, 34)
        mapping = map_public_investment_scheme("Water & Sanitation", budget["priority_band"], "CORRELATED")
        self.assertEqual(mapping["scheme_id"], "JJM-RURAL-WATER")
        self.assertTrue(mapping["review_required"])

    def test_hotspot_aggregation_groups_sanitized_events(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "demand_events.jsonl")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(json.dumps({
                    "district_id": "IND-BR-01", "district_name": "Katihar",
                    "category": "Water & Sanitation", "channel": "whatsapp_bot",
                    "demand_volume": 1, "priority_urgency_score": 72.0,
                    "estimated_capex_inr": 850000, "checker_status": "APPROVED",
                    "coordinates": {"lat": 25.5414, "lng": 87.5714},
                }) + "\n")
            original = hotspot_module.EVENTS_PATH
            hotspot_module.EVENTS_PATH = path
            try:
                result = aggregate_hotspots()
            finally:
                hotspot_module.EVENTS_PATH = original
        self.assertEqual(result["event_count"], 1)
        self.assertEqual(result["hotspots"][0]["verified_count"], 1)
        self.assertEqual(result["hotspots"][0]["district_name"], "Katihar")


if __name__ == "__main__":
    unittest.main()
