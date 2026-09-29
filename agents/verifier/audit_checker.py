"""
audit_checker.py - Independent Checker Logic for PolicyAuditor Sub-Agent.
Enforces Segregation of Duties (DUTIES.md) and Invariants (RULES.md).
"""
import re
import json
import hashlib
from typing import Dict, Any

PHONE_OR_ID_LEAK = re.compile(r'\b\d{10}\b|\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b')

def verify_proposal(maker_proposal: Dict[str, Any]) -> Dict[str, Any]:
    """
    Audits Maker's output package before dispatch to Policymaker dashboard.
    Returns status: PASSED or REJECTED with specific audit trail.
    """
    violations = []

    # 1. Check for PII leakage in sanitized text or response
    text_to_check = str(maker_proposal.get("citizen_text", "")) + " " + str(maker_proposal.get("recommendation", ""))
    if PHONE_OR_ID_LEAK.search(text_to_check):
        violations.append("CRITICAL_SECURITY_LEAK: Unmasked phone or national ID detected in proposal payload.")

    # 2. Check for PUS bounds (0.0 to 100.0)
    pus = maker_proposal.get("priority_urgency_score", 0.0)
    if not (0.0 <= pus <= 100.0):
        violations.append(f"CALCULATION_ERROR: Priority Urgency Score {pus} out of legal bounds [0.0, 100.0].")

    # 3. Check for Capex sanity
    capex = maker_proposal.get("estimated_capex_inr", 0)
    if capex <= 0 or capex > 500000000: # 50 Crore ceiling for fast-track DPI
        violations.append(f"BUDGET_CEILING_BREACH: Capex INR {capex} invalid or exceeds 50 Crore fast-track threshold.")

    # 4. Check for Beneficiaries count
    beneficiaries = maker_proposal.get("estimated_beneficiaries", 0)
    if beneficiaries <= 0:
        violations.append("DEMOGRAPHIC_ERROR: Zero or negative beneficiaries projected.")

    is_passed = len(violations) == 0

    # Cryptographic verification seal
    payload_str = json.dumps(maker_proposal, sort_keys=True)
    verification_hash = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()[:16]

    return {
        "status": "APPROVED" if is_passed else "REJECTED",
        "checker_agent": "PolicyAuditor (verifier)",
        "violations_count": len(violations),
        "violations": violations,
        "verification_hash": f"SEAL-{verification_hash.upper()}",
        "confidence_score": 0.98 if is_passed else 0.40,
        "recommendation_status": "CERTIFIED_FOR_GOVERNMENT_ALLOCATION" if is_passed else "RECALIBRATION_REQUIRED"
    }

if __name__ == "__main__":
    sample_proposal = {
        "citizen_text": "Sanitized pipeline request at Katihar",
        "priority_urgency_score": 78.4,
        "estimated_capex_inr": 850000,
        "estimated_beneficiaries": 2500,
        "recommendation": "Deploy Solar Borewell + RO/UV Plant"
    }
    print(json.dumps(verify_proposal(sample_proposal), indent=2))
