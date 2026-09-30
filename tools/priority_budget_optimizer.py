"""
priority_budget_optimizer.py - Computes Priority Urgency Scores (PUS) and Capital Expenditure (Capex).
Part of JanSetu AI (OpenGAP Standard).
Deterministic calculation engine ensuring zero hallucination of public works budgets.
"""
import os
import json
from typing import Dict, Any

SOR_PATH = os.path.join(os.path.dirname(__file__), "..", "knowledge", "infrastructure_sor_rates.json")

def load_sor_database() -> Dict[str, Any]:
    with open(SOR_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def optimize_priority_and_budget(
    category: str,
    mpi_deprivation: float,
    sector_deficit: float,
    demand_volume: int = 15,
    unit_multiplier: float = 1.0
) -> Dict[str, Any]:
    """
    Computes deterministic priority score and budget sizing according to public finance schedules.
    """
    if not isinstance(demand_volume, int) or isinstance(demand_volume, bool) or demand_volume < 0:
        raise ValueError("demand_volume must be a non-negative integer")
    if not 0.0 <= float(mpi_deprivation) <= 1.0:
        raise ValueError("mpi_deprivation must be between 0.0 and 1.0")
    if not 0.0 <= float(sector_deficit) <= 1.0:
        raise ValueError("sector_deficit must be between 0.0 and 1.0")
    if not 0.0 < float(unit_multiplier) <= 100.0:
        raise ValueError("unit_multiplier must be greater than 0 and at most 100")
    sor_db = load_sor_database()
    rates = sor_db.get("schedule_of_rates", [])

    matched_sor = None
    for r in rates:
        if r["category"].lower() == category.lower():
            matched_sor = r
            break
    if not matched_sor:
        matched_sor = rates[0]

    # Normalize demand volume (assume threshold 50 requests is 1.0)
    norm_demand = min(1.0, demand_volume / 50.0)

    # Formula: Priority Urgency Score (0 - 100)
    # PUS = (0.35 * norm_demand + 0.35 * mpi_deprivation + 0.30 * sector_deficit) * 100
    raw_score = (0.35 * norm_demand) + (0.35 * mpi_deprivation) + (0.30 * sector_deficit)
    pus_score = round(raw_score * 100, 1)

    # Sizing Capex
    base_cost = matched_sor["standard_cost_inr"]
    estimated_capex_inr = round(base_cost * unit_multiplier)
    estimated_capex_usd = round(estimated_capex_inr / 83.5) # Standard exchange rate reference

    beneficiaries = int(matched_sor["estimated_beneficiaries_per_unit"] * unit_multiplier)

    # Benefit-to-Cost Index (Beneficiaries per Lakh INR)
    bcr_index = round((beneficiaries / (estimated_capex_inr / 100000)), 2)

    # Urgency Classification
    if pus_score >= 70.0:
        band = "TIER_1_CRITICAL_FAST_TRACK"
        approval_flow = "Accelerated Disaster & Vulnerability Fund"
    elif pus_score >= 50.0:
        band = "TIER_2_HIGH_PRIORITY_ANNUAL_PLAN"
        approval_flow = "State Consolidated Capital Works Scheme"
    else:
        band = "TIER_3_ROUTINE_MUNICIPAL_WORKS"
        approval_flow = "Local Panchayat / Municipal Maintenance Grant"

    return {
        "status": "OPTIMIZED",
        "priority_urgency_score": pus_score,
        "priority_band": band,
        "approval_flow": approval_flow,
        "recommended_project_type": matched_sor["project_type"],
        "estimated_capex_inr": estimated_capex_inr,
        "estimated_capex_usd": estimated_capex_usd,
        "estimated_beneficiaries": beneficiaries,
        "benefit_cost_ratio_index": bcr_index,
        "lead_time_days": matched_sor["lead_time_days"],
        "operational_lifetime_years": matched_sor["operational_lifetime_years"],
        "demand_volume": demand_volume,
        "unit_multiplier": unit_multiplier,
        "audit_hash_input": f"{category}:{mpi_deprivation}:{sector_deficit}:{demand_volume}"
    }

if __name__ == "__main__":
    print(json.dumps(optimize_priority_and_budget("Water & Sanitation", 0.428, 0.476, 24), indent=2))
