# Calibration Dialogue (Few-Shot Reference)

## Example 1: Multilingual Citizen Input Ingestion
**User Input (Hindi):** "हमारे गांव में पिछले 4 दिन से पीने का पानी नहीं आ रहा है, पाइपलाइन टूटी हुई है।"
**Agent Internal Reasoning:**
1. Detect Language: Hindi (hi)
2. Extract Intent: Drinking water supply disruption / broken pipeline
3. Extract Severity: Critical (4 days duration, essential public utility)
4. Invoke Tool: `infra_ticket_router`
5. Formulate Response: Multilingual confirmation with ticket tracking ID and routed authority.
