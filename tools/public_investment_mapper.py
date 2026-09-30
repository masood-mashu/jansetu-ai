"""Maps a costed category to a reviewable public investment scheme."""
import json
import os
from typing import Any, Dict


SCHEMES_PATH = os.path.join(os.path.dirname(__file__), "..", "knowledge", "public_investment_schemes.json")


def map_public_investment_scheme(category: str, priority_band: str, baseline_status: str) -> Dict[str, Any]:
    with open(SCHEMES_PATH, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    mapping = data.get("schemes", {}).get(category)
    if not mapping:
        return {
            "status": "NO_CURATED_MATCH",
            "review_required": True,
            "reason": "Category is outside the curated pilot scheme map.",
        }
    return {
        "status": "CURATED_REVIEW_MATCH",
        "scheme_id": mapping["scheme_id"],
        "scheme_name": mapping["scheme_name"],
        "admin_level": mapping["admin_level"],
        "eligibility_signal": mapping["eligibility_signal"],
        "source_reference": mapping["source_reference"],
        "priority_band": priority_band,
        "baseline_status": baseline_status,
        "review_required": True,
        "mapping_version": data.get("version", "unknown"),
    }
