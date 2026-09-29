# JanSetu AI — Hack2skill Final Submission Copy

---

## 1. Title & Tagline

**JanSetu AI (जनसेतु): The People's Bridge**  
*Turning a voice note in any language into a verified, costed public works proposal, as an open-source Digital Public Good.*

---

## 2. Short Summary (~85 words)

JanSetu AI is an open-source, multilingual Digital Public Good that converts citizen voice and text requests into verified capital-works recommendations. Gemini handles vernacular understanding across 7 languages; deterministic OpenGAP Python tools handle PII redaction, NITI Aayog MPI correlation and Schedule-of-Rates costing. A Maker-Checker design has a Gemini-powered advocate propose projects and an independent PolicyAuditor verify the math, check for PII leaks and issue a tamper-evident SEAL. Policymakers get ranked demand hotspots with auditable justification, built for Aspirational Districts and BRICS-scale reuse.

---

## 3. The Problem & Why Existing DPI Fails

Citizen development requests exist, but they're scattered across voice notes, SMS and WhatsApp in regional languages, invisible to the people who allocate capital expenditure. Existing DPI and grievance portals fail in three ways:

- **Form-first, English-first design:** Portals need literacy, connectivity and a form. The people with the highest deprivation are the least likely to file.
- **No link to spending:** Grievances sit in a queue; they're never joined to district deprivation data (MPI) or investment schedules, so spending drifts away from need.
- **Unverifiable AI risk:** Dropping an LLM on raw citizen data creates PII exposure, hallucinated budgets and no audit trail, which is unacceptable for governance.

**Result:** Misaligned public spending, unaddressed infrastructure gaps and zero impact measurement.

---

## 4. Our Solution: JanSetu AI on the OpenGAP Standard

JanSetu is built on **OpenGAP (Open Git Agent Protocol)**: the agent *is* a Git repository, so its identity, rules, duties and knowledge are versioned, diffable and auditable like code.

| OpenGAP file | Role |
|---|---|
| `SOUL.md` | Non-partisan civic identity |
| `RULES.md` | Hard invariants: zero PII to the LLM, zero hallucinated figures |
| `DUTIES.md` | Segregation of duties (Maker vs Checker) |
| `knowledge/` | District MPI baselines + Public Works Schedule of Rates |
| `tools/` | Deterministic sanitizer, GIS correlator, budget optimizer (MCP-compatible schemas) |

**Pipeline:** Ingest → Sanitize → Ground in census/MPI → Score → Cost → Maker proposes → Checker audits → SEAL.

**Deterministic Priority Urgency Score:**  
$$\text{PUS} = [0.35 \times \text{Demand Volume} + 0.35 \times \text{Poverty Index} + 0.30 \times \text{Infrastructure Deficit}] \times 100$$

Same input always gives the same score, so policymakers can defend every ranking. The framework is model-agnostic (`AGENTS.md` fallback) and runs locally with a zero-dependency server, so any state or BRICS nation can fork it.

---

## 5. Google Cloud & Gemini Integration Breakdown

**Principle: Probabilistic AI for language, deterministic code for anything that must be right.**

| Layer | Handled by | Why |
|---|---|---|
| Vernacular voice/text understanding (Hindi, Tamil, Telugu, Bengali, Marathi, Portuguese, English), code-mixed speech, intent + infrastructure-category extraction | **Google Gemini 2.0 Flash / 1.5 Pro** | Handles audio, dialect and noisy input natively without a separate ASR pipeline |
| Maker: drafting the capital project proposal and the acknowledgment back to the citizen **in their own language** | **Google Gemini** | Generative, language-sensitive contextual synthesis |
| Checker narrative: plain-language audit explanation | **Google Gemini** | Readable, administrative clarity for district magistrates |
| PII redaction (Aadhaar, phone, email) | **Deterministic Python** (`citizen_ingest_sanitizer.py`) | Runs *before* any LLM call; zero model discretion |
| Census/MPI correlation | **Deterministic Python** (`gis_demographic_correlator.py`) against versioned baseline JSON | Verifiable, reproducible against NITI Aayog benchmarks |
| PUS + Capex sizing | **Deterministic Python** (`priority_budget_optimizer.py`) using official Schedule of Rates (SoR) | LLMs must never do budget math |
| Budget caps, math re-verification, PII leak check, SEAL | **PolicyAuditor Sub-Agent** (`agents/verifier/audit_checker.py`) | Separate duty, independent cryptographic sign-off |

**Google Cloud Fit:** Built for Gemini API and Vertex AI endpoints; containerized microservices ready for Google Cloud Run deployment; all decisions recorded in a persistent OpenGAP audit ledger (`memory/runtime/dailylog.md`).

---

## 6. End-to-End Walkthrough: Katihar, Bihar

1. **Voice note (Hindi):** A resident of Katihar sends a message reporting contaminated drinking water and pipeline leaks in Barari village, including their personal phone number (`9876543210`) and Aadhaar (`4589-1234-5678`).
2. **Gemini ingestion:** Language detected as Hindi (`hi`); intent classified as *Water & Sanitation*; aggregated with 34 related demand signals from the same block.
3. **PII scrub (before reasoning):** The deterministic sanitizer strips phone and Aadhaar to `[PHONE_REDACTED]` and `[NATIONAL_ID_REDACTED]`. Zero sensitive tokens reach the LLM.
4. **Census/MPI correlation:** Katihar matched to baseline (`IND-BR-01`): Multi-dimensional Poverty Index (MPI) **0.428**, water coverage deficit **47.6%**, classified as an Aspirational District.
5. **PUS scoring:** Demand volume (34/50) + MPI (0.428) + Water deficit (0.476) → **PUS = 53.1 / 100**, placing it in Tier-2 High-Priority Capital Works.
6. **Costing:** Optimizer maps the need to an SoR-priced public work: **Solar-powered Borewell + RO/UV Treatment Plant, ₹8.5 Lakhs** ($10,180 USD), benefiting 2,500 citizens with a Benefit-to-Cost Ratio (BCR) of 294.12.
7. **Maker (CitizenAdvocate):** Drafts the proposal and a personalized **Hindi acknowledgment** back to the citizen (`"नमस्ते। आपकी Water & Sanitation संबंधी मांग जनसेतु प्रणाली में दर्ज कर ली गई है..."`).
8. **Checker (PolicyAuditor):** Re-computes the math, verifies budget ceiling, confirms zero PII leakage, and stamps **`SEAL-73007425ECBD593E`** with 0.98 confidence.
9. **Policymaker dashboard:** District Magistrate sees the live geospatial hotspot, formulaic score breakdown, costed SoR project, and tamper-evident seal.

**Outcome:** A fragmented Hindi voice note becomes an auditable, budget-aligned capital works proposal, and the citizen receives immediate reassurance in their native tongue.

---

## 7. Community & Socio-Economic Impact

- **MeitY DPG alignment:** Open source (Apache 2.0), reusable, standards-based (OpenGAP, MCP-compatible tool schemas), privacy-by-design, with `compliance/` documentation covering Responsible AI and Digital Public Good criteria.
- **Aspirational Districts:** Directs capital expenditure to districts where deprivation is highest and voice access is often the *only* accessible channel, ensuring the most vulnerable citizens are heard.
- **Spending accountability:** Directly connects citizen demand to deprivation data and costed works, giving governments a measurable path from "request" to "investment" to "impact."
- **Trust by design:** Zero-PII guardrails, deterministic math, and a Maker-Checker seal eliminate hallucinated public works allocations.
- **BRICS scale:** Baseline census files and Schedule of Rates are swappable per country; Portuguese support is already tested for Juazeiro, Brazil, allowing one framework to serve districts, municipalities, and partner nations without re-architecting.
