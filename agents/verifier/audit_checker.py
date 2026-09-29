"""
audit_checker.py - Independent Checker Logic for PolicyAuditor Sub-Agent.
Enforces Segregation of Duties (DUTIES.md) and Invariants (RULES.md).
Features independent mathematical formula re-verification and HMAC cryptographic seals.
"""
import os
import re
import json
import hmac
import hashlib
from typing import Dict, Any

PHONE_OR_ID_LEAK = re.compile(
    r'(?:(?:\+|00)?91[\s.-]?)?(?:[6-9]\d{4}[\s.-]?\d{5}|0?[6-9]\d{9})\b|'
    r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
)

def verify_proposal(maker_proposal: Dict[str, Any]) -> Dict[str, Any]:
    """
    Audits Maker's output package before dispatch to Policymaker dashboard.
    1. Independent formula re-computation (PUS math audit)
    2. Deep PII leakage scan
    3. Public works Capex ceiling audit
    4. Tamper-evident HMAC-SHA256 seal generation
    """
    violations = []

    # 1. Check for PII leakage in sanitized text or response
    text_to_check = str(maker_proposal.get("citizen_text", "")) + " " + str(maker_proposal.get("recommendation", ""))
    if PHONE_OR_ID_LEAK.search(text_to_check):
        violations.append("CRITICAL_SECURITY_LEAK: Unmasked phone or national ID detected in proposal payload.")

    pus = maker_proposal.get("priority_urgency_score", 0.0)

    # 2. Independent Mathematical Formula Re-Verification
    demand_vol = maker_proposal.get("demand_volume")
    mpi = maker_proposal.get("mpi_deprivation")
    deficit = maker_proposal.get("sector_deficit")

    if demand_vol is not None and mpi is not None and deficit is not None:
        norm_demand = min(1.0, float(demand_vol) / 50.0)
        expected_pus = round(((0.35 * norm_demand) + (0.35 * float(mpi)) + (0.30 * float(deficit))) * 100, 1)
        if abs(expected_pus - pus) > 0.5:
            violations.append(f"MATH_RECOMPUTE_MISMATCH: Maker PUS {pus} diverges from Checker verified PUS {expected_pus}.")

    # 3. Check for PUS bounds (0.0 to 100.0)
    if not (0.0 <= pus <= 100.0):
        violations.append(f"CALCULATION_ERROR: Priority Urgency Score {pus} out of legal bounds [0.0, 100.0].")

    # 4. Check for Capex sanity
    capex = maker_proposal.get("estimated_capex_inr", 0)
    if capex <= 0 or capex > 500000000: # 50 Crore ceiling for fast-track DPI
        violations.append(f"BUDGET_CEILING_BREACH: Capex INR {capex} invalid or exceeds 50 Crore fast-track threshold.")

    # 5. Check for Beneficiaries count
    beneficiaries = maker_proposal.get("estimated_beneficiaries", 0)
    if beneficiaries <= 0:
        violations.append("DEMOGRAPHIC_ERROR: Zero or negative beneficiaries projected.")

    is_passed = len(violations) == 0

    # Cryptographic verification seal (HMAC-SHA256 tamper-evident seal)
    secret_key = os.getenv("JANSETU_AUDIT_KEY", "JANSETU-OPENGAP-ROOT-GOVERNANCE-KEY").encode('utf-8')
    payload_bytes = json.dumps(maker_proposal, sort_keys=True).encode('utf-8')
    verification_hash = hmac.new(secret_key, payload_bytes, hashlib.sha256).hexdigest()[:16].upper()

    return {
        "status": "APPROVED" if is_passed else "REJECTED",
        "checker_agent": "PolicyAuditor (verifier)",
        "violations_count": len(violations),
        "violations": violations,
        "math_recomputed_and_verified": is_passed and (demand_vol is not None),
        "verification_hash": f"SEAL-{verification_hash}",
        "confidence_score": 0.98 if is_passed else 0.40,
        "recommendation_status": "CERTIFIED_FOR_GOVERNMENT_ALLOCATION" if is_passed else "RECALIBRATION_REQUIRED"
    }

if __name__ == "__main__":
    sample_proposal = {
        "citizen_text": "Sanitized pipeline request at Katihar",
        "priority_urgency_score": 53.1,
        "demand_volume": 34,
        "mpi_deprivation": 0.428,
        "sector_deficit": 0.476,
        "estimated_capex_inr": 850000,
        "estimated_beneficiaries": 2500,
        "recommendation": "Deploy Solar Borewell + RO/UV Plant"
    }
    print(json.dumps(verify_proposal(sample_proposal), indent=2))
