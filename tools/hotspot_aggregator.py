"""Deterministic demand-hotspot aggregation over sanitized event records."""
import json
import os
from collections import defaultdict
from typing import Any, Dict, List


EVENTS_PATH = os.path.join(os.path.dirname(__file__), "..", ".gitagent", "demand_events.jsonl")


def load_demand_events() -> List[Dict[str, Any]]:
    if not os.path.exists(EVENTS_PATH):
        return []
    events = []
    with open(EVENTS_PATH, "r", encoding="utf-8") as handle:
        for line in handle:
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    events.append(item)
            except json.JSONDecodeError:
                continue
    return events


def aggregate_hotspots(limit: int = 20) -> Dict[str, Any]:
    """Group demand by district and category, preserving transparent metrics."""
    events = load_demand_events()
    groups = defaultdict(lambda: {
        "request_count": 0, "demand_volume": 0, "pus_total": 0.0,
        "verified_count": 0, "channels": set(), "coordinates": None,
        "capex_inr": 0,
    })
    district_names = {}
    for event in events:
        key = (event.get("district_id", "UNKNOWN"), event.get("category", "Unknown"))
        district_names[key[0]] = event.get("district_name", key[0])
        group = groups[key]
        group["request_count"] += 1
        group["demand_volume"] += int(event.get("demand_volume", 0))
        group["pus_total"] += float(event.get("priority_urgency_score", 0.0))
        group["verified_count"] += int(event.get("checker_status") == "APPROVED")
        group["channels"].add(event.get("channel", "unknown"))
        group["coordinates"] = event.get("coordinates") or group["coordinates"]
        group["capex_inr"] += int(event.get("estimated_capex_inr", 0))

    hotspots = []
    for (district_id, category), group in groups.items():
        request_count = group["request_count"]
        average_pus = round(group["pus_total"] / request_count, 1) if request_count else 0.0
        hotspots.append({
            "district_id": district_id,
            "district_name": district_names.get(district_id, district_id),
            "category": category,
            "request_count": request_count,
            "demand_volume": group["demand_volume"],
            "average_priority_urgency_score": average_pus,
            "hotspot_score": round(min(100.0, average_pus + min(25.0, request_count * 2.5)), 1),
            "verified_count": group["verified_count"],
            "channels": sorted(group["channels"]),
            "coordinates": group["coordinates"],
            "aggregated_capex_inr": group["capex_inr"],
        })
    hotspots.sort(key=lambda item: (item["hotspot_score"], item["demand_volume"]), reverse=True)
    return {"status": "AGGREGATED", "event_count": len(events), "hotspots": hotspots[:max(1, min(limit, 100))]}
