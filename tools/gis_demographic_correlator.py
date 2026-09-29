"""
gis_demographic_correlator.py - Cross-references citizen locations with national demographic indices.
Part of JanSetu AI (OpenGAP Standard).
"""
import os
import json
from typing import Dict, Any, Optional

BASELINE_PATH = os.path.join(os.path.dirname(__file__), "..", "knowledge", "brics_districts_baseline.json")

def load_districts_database() -> Dict[str, Any]:
    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def correlate_district_demographics(location_name: str, category: str = "Water & Sanitation") -> Dict[str, Any]:
    """
    Finds the closest district match and computes infrastructure vulnerability metrics.
    """
    db = load_districts_database()
    districts = db.get("districts", [])

    matched = None
    clean_query = location_name.lower().strip()

    # Search for district name in query or query in district name
    for d in districts:
        name = d["name"].lower()
        state = d["state_province"].lower()
        if name in clean_query or clean_query in name or state in clean_query:
            matched = d
            break

    # If not matched in pilot baseline, return benchmark average with clear status flag
    if not matched:
        return {
            "status": "DISTRICT_NOT_IN_BASELINE",
            "pilot_notice": f"Location '{location_name}' outside 6-district pilot dataset. Applied national baseline benchmarks.",
            "district_id": "PILOT-BENCHMARK-AVG",
            "district_name": location_name.title() if location_name else "National Pilot Benchmark",
            "state_province": "Pilot Benchmark",
            "country": "India",
            "total_population": 1500000,
            "rural_percentage": 75.0,
            "mpi_deprivation_index": 0.280,
            "sector_evaluated": category,
            "sector_deficit_score": 0.400,
            "budget_utilization_track_record": 80.0,
            "coordinates": {"lat": 20.5937, "lng": 78.9629},
            "is_aspirational_priority": False
        }

    # Determine Sector Deficit Index (0.0 to 1.0)
    deficit_score = 0.5
    if category == "Water & Sanitation":
        # Deficit is 100 - coverage %
        deficit_score = round((100 - matched["drinking_water_coverage_pct"]) / 100.0, 3)
    elif category == "Primary Healthcare":
        deficit_score = round(matched["phc_doctor_deficit_pct"] / 100.0, 3)
    elif category == "Rural Connectivity":
        deficit_score = round((100 - matched["road_paved_connectivity_pct"]) / 100.0, 3)
    elif category == "Power & Energy":
        deficit_score = round((24 - matched["grid_electricity_reliability_hrs"]) / 24.0, 3)
    elif category == "Education & Digital Literacy":
        deficit_score = round((100 - matched["primary_schools_with_electricity_pct"]) / 100.0, 3)

    return {
        "status": "CORRELATED",
        "district_id": matched["id"],
        "district_name": matched["name"],
        "state_province": matched["state_province"],
        "country": matched["country"],
        "total_population": matched["population"],
        "rural_percentage": matched["rural_percentage"],
        "mpi_deprivation_index": matched["mpi_deprivation_index"],
        "sector_evaluated": category,
        "sector_deficit_score": deficit_score,
        "budget_utilization_track_record": matched["historical_budget_utilization_pct"],
        "coordinates": matched["coordinates"],
        "is_aspirational_priority": matched["mpi_deprivation_index"] >= 0.35
    }

if __name__ == "__main__":
    print(json.dumps(correlate_district_demographics("Katihar", "Water & Sanitation"), indent=2))
