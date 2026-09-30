"""
engine.py - Core OpenGAP Runtime Engine for JanSetu AI.
Powers the Maker-Checker pipeline with Google Gemini 2.5 Flash (fallbacks: 2.0 Flash, 1.5 Pro).
Runs seamlessly both with live Gemini API keys and standalone deterministic mode.
"""
import os
import sys
import json
import time
import datetime
import hashlib
from typing import Dict, Any, Optional

# Ensure tools and agents are on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from tools.citizen_ingest_sanitizer import sanitize_and_parse_request
from tools.gis_demographic_correlator import correlate_district_demographics
from tools.priority_budget_optimizer import optimize_priority_and_budget
from tools.public_investment_mapper import map_public_investment_scheme
from agents.verifier.audit_checker import verify_proposal

# Google Generative AI optional import
try:
    import google.generativeai as genai
    HAS_GOOGLE_GENAI = True
except ImportError:
    HAS_GOOGLE_GENAI = False

class JanSetuEngine:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            env_file = os.path.join(BASE_DIR, ".env")
            if os.path.exists(env_file):
                try:
                    with open(env_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("GEMINI_API_KEY="):
                                self.api_key = line.split("=", 1)[1].strip("'\" ")
                                os.environ["GEMINI_API_KEY"] = self.api_key
                                break
                except Exception:
                    pass
        self.model = None
        self._init_gemini()
        self._ensure_audit_dirs()

    def _init_gemini(self):
        self.model_name = None
        if self.api_key:
            import urllib.request
            # Auto-detect available live Google Gemini models (compatible with both AIzaSy and AQ keys)
            for candidate in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-flash-latest"]:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate}:generateContent?key={self.api_key}"
                try:
                    test_payload = json.dumps({"contents": [{"parts": [{"text": "ping"}]}]}).encode("utf-8")
                    req = urllib.request.Request(url, data=test_payload, headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        if resp.status == 200:
                            self.model_name = candidate
                            break
                except Exception:
                    continue

            if self.model_name:
                print(f"[JanSetu Engine] Connected to Google {self.model_name} (Live Cloud Active).")
            elif HAS_GOOGLE_GENAI:
                try:
                    genai.configure(api_key=self.api_key)
                    self.model_name = "gemini-2.0-flash"
                    self.model = genai.GenerativeModel(model_name=self.model_name, system_instruction=self._load_soul_and_rules())
                    print(f"[JanSetu Engine] Connected to Google {self.model_name} via SDK.")
                except Exception:
                    self.model_name = None
                    print("[JanSetu Engine] WARNING: Key set but Gemini endpoints unreachable, using deterministic fallback.")
            else:
                print("[JanSetu Engine] WARNING: Key set but Gemini endpoints unreachable, using deterministic fallback.")
        else:
            print("[JanSetu Engine] Standalone OpenGAP deterministic engine active (Live Gemini Ready).")

    def _load_soul_and_rules(self) -> str:
        soul_path = os.path.join(BASE_DIR, "SOUL.md")
        rules_path = os.path.join(BASE_DIR, "RULES.md")
        soul_text = ""
        rules_text = ""
        if os.path.exists(soul_path):
            with open(soul_path, "r", encoding="utf-8") as f:
                soul_text = f.read()
        if os.path.exists(rules_path):
            with open(rules_path, "r", encoding="utf-8") as f:
                rules_text = f.read()
        return f"{soul_text}\n\n{rules_text}"

    def _ensure_audit_dirs(self):
        gitagent_dir = os.path.join(BASE_DIR, ".gitagent")
        os.makedirs(gitagent_dir, exist_ok=True)

    def process_citizen_demand(
        self,
        raw_text: str,
        channel: str = "voice_note",
        location_hint: str = "",
        demand_volume: int = 34
    ) -> Dict[str, Any]:
        """
        Full OpenGAP Maker-Checker pipeline:
        1. Sanitize & extract intent (PII scrub)
        2. Correlate with Census & MPI Deprivation index
        3. Optimize priority urgency score & budget
        4. Synthesize citizen response + policymaker memo (via Gemini or deterministic)
        5. Verify via PolicyAuditor Checker Sub-Agent
        6. Append to immutable GitAgent audit trail
        """
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"

        # Step 1: Tool - Citizen Ingestion Sanitizer
        ingest_res = sanitize_and_parse_request(raw_text, channel=channel, location_hint=location_hint)
        detected_cat = ingest_res["detected_category"]
        detected_lang = ingest_res["detected_language"]
        loc = location_hint or ingest_res.get("location_hint", "Katihar, Bihar")

        # Step 2: Tool - GIS Demographic Correlator
        gis_res = correlate_district_demographics(loc, category=detected_cat)

        # Step 3: Tool - Priority Budget Optimizer
        budget_res = optimize_priority_and_budget(
            category=detected_cat,
            mpi_deprivation=gis_res["mpi_deprivation_index"],
            sector_deficit=gis_res["sector_deficit_score"],
            demand_volume=demand_volume
        )
        budget_res["scheme_mapping"] = map_public_investment_scheme(
            detected_cat,
            budget_res["priority_band"],
            gis_res["status"],
        )

        # Step 4: Maker Synthesis (Gemini or Native Expert Synthesis)
        maker_synthesis = self._synthesize_advisory(
            raw_text=raw_text,
            sanitized_text=ingest_res["sanitized_text"],
            category=detected_cat,
            language=detected_lang,
            gis_data=gis_res,
            budget_data=budget_res
        )

        # Step 5: Checker Sub-Agent Verification (Segregation of Duties)
        checker_input = {
            "citizen_text": ingest_res["sanitized_text"],
            "maker_synthesis": maker_synthesis,
            "category": detected_cat,
            "priority_urgency_score": budget_res["priority_urgency_score"],
            "demand_volume": demand_volume,
            "mpi_deprivation": gis_res["mpi_deprivation_index"],
            "sector_deficit": gis_res["sector_deficit_score"],
            "estimated_capex_inr": budget_res["estimated_capex_inr"],
            "estimated_beneficiaries": budget_res["estimated_beneficiaries"],
            "recommendation": budget_res["recommended_project_type"],
            "district": gis_res["district_name"],
            "baseline_status": gis_res["status"]
        }
        audit_res = verify_proposal(checker_input)

        # Step 6: Package Final Response Dossier
        response_package = {
            "metadata": {
                "system": "JanSetu AI (जनसेतु)",
                "spec": "OpenGAP v0.1.0",
                "timestamp": timestamp,
                "model_engine": f"google:{self.model_name}" if self.model_name else "opengap:deterministic-engine",
                "verification_seal": audit_res["verification_hash"]
            },
            "ingestion": ingest_res,
            "demographic_context": gis_res,
            "priority_and_budget": budget_res,
            "maker_synthesis": maker_synthesis,
            "checker_audit": audit_res
        }

        # Step 7: Record Audit Log
        self._record_audit_log(response_package)

        return response_package

    def _synthesize_advisory(
        self,
        raw_text: str,
        sanitized_text: str,
        category: str,
        language: str,
        gis_data: Dict[str, Any],
        budget_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synthesizes citizen reply and policymaker memo."""
        district = gis_data["district_name"]
        state = gis_data["state_province"]
        pus = budget_data["priority_urgency_score"]
        capex_inr = budget_data["estimated_capex_inr"]
        capex_lakh = round(capex_inr / 100000, 2)
        proj_type = budget_data["recommended_project_type"]
        beneficiaries = budget_data["estimated_beneficiaries"]
        scheme = budget_data.get("scheme_mapping", {})
        scheme_name = scheme.get("scheme_name", "scheme review required")

        if self.model_name and self.api_key:
            try:
                prompt = f"""
                You are JanSetu AI, speaking to a citizen and a district magistrate.
                The citizen said: "{sanitized_text}"
                Language: {language}
                Location: {district}, {state}
                Category: {category}
                Priority Urgency Score: {pus}/100
                Recommended Project: {proj_type} (Capex: ₹{capex_lakh} Lakhs for {beneficiaries} citizens)
                Public Investment Scheme Mapping: {scheme_name}

                Generate a JSON object with:
                1. "citizen_acknowledgment": Warm, respectful confirmation in {language} confirming that their grievance has been logged, geotagged to {district}, and escalated with priority tier {budget_data['priority_band']}.
                2. "policymaker_briefing_memo": A professional 3-sentence executive summary for the District Magistrate / Chief Secretary explaining the infrastructure deficit, demand cluster, and why this ₹{capex_lakh} Lakh investment is recommended.
                """
                import urllib.request
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
                payload = json.dumps({
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json"}
                }).encode("utf-8")
                headers = {
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key
                }
                req = urllib.request.Request(url, data=payload, headers=headers)
                with urllib.request.urlopen(req, timeout=12) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    cand = resp_data.get("candidates", [{}])[0]
                    text = cand.get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                    if text:
                        data = json.loads(text)
                        if isinstance(data, dict) and data.get("citizen_acknowledgment") and data.get("policymaker_briefing_memo"):
                            return data
                        else:
                            print("[JanSetu Engine] Warning: Gemini JSON missing required keys. Falling back.")
            except Exception as e:
                print(f"[JanSetu Engine] Fallback to deterministic synthesis: {e}")

        # Deterministic multilingual generator
        hi_cat_map = {
            "Water & Sanitation": "पेयजल एवं स्वच्छता",
            "Primary Healthcare": "प्राथमिक स्वास्थ्य",
            "Rural Connectivity": "ग्रामीण सड़क संपर्क",
            "Power & Energy": "विद्युत आपूर्ति",
            "Education & Digital Literacy": "शिक्षा एवं डिजिटल साक्षरता"
        }
        localized_cat = hi_cat_map.get(category, category)
        if language == "hi":
            citizen_ack = f"नमस्ते। आपकी {localized_cat} संबंधी मांग जनसेतु प्रणाली में दर्ज कर ली गई है। आपका क्षेत्र {district}, {state} हमारे प्राथमिकता डैशबोर्ड में सम्मिलित है। आपकी समस्या को प्राथमिकता स्कोर {pus}/100 ({budget_data['priority_band']}) के साथ जिला प्रशासन को कार्रवाई हेतु प्रेषित कर दिया गया है।"
        elif language == "ta":
            citizen_ack = f"வணக்கம். உங்கள் {category} கோரிக்கை ஜனசேது அமைப்பில் பதிவு செய்யப்பட்டுள்ளது. {district}, {state} பகுதிக்கான முன்னுரிமை மதிப்பெண் {pus}/100 ஆக கணக்கிடப்பட்டு மாவட்ட நிர்வாகத்திற்கு அனுப்பப்பட்டுள்ளது."
        elif language == "te":
            citizen_ack = f"నమస్కారం. మీ {category} అభ్యర్థన జనసేతు వ్యవస్థలో విజయవంతంగా నమోదు చేయబడింది. {district}, {state} జిల్లా ప్రాధాన్యత స్కోరు {pus}/100 తో అధికారులకు సిఫార్సు చేయబడింది."
        elif language == "pt":
            citizen_ack = f"Olá. A sua solicitação de {category} foi registrada na plataforma JanSetu. O distrito de {district} recebeu uma pontuação de urgência de {pus}/100 e foi encaminhado para as autoridades competentes."
        else:
            citizen_ack = f"Greetings. Your citizen request regarding {category} in {district}, {state} has been securely registered on the JanSetu Digital Public Infrastructure platform. It has been awarded a Priority Urgency Score of {pus}/100 and routed to the public works division."

        tier_tag = "CRITICAL FAST-TRACK PROPOSAL" if pus >= 70.0 else ("PRIORITY CAPITAL WORKS PROPOSAL" if pus >= 50.0 else "MUNICIPAL WORKS PROPOSAL")
        policy_memo = (
            f"{tier_tag}: Demand cluster detected in {district}, {state} (MPI Deprivation Index: {gis_data['mpi_deprivation_index']}). "
            f"JanSetu recommends capital provisioning for '{proj_type}' with an estimated capex of ₹{capex_lakh} Lakhs ($ {budget_data['estimated_capex_usd']:,} USD), "
            f"mapped for review against '{scheme_name}' ({scheme.get('scheme_id', 'NO_CURATED_MATCH')}). "
            f"The proposal directly benefits {beneficiaries:,} citizens with a Benefit-Cost Ratio of {budget_data['benefit_cost_ratio_index']}."
        )

        return {
            "citizen_acknowledgment": citizen_ack,
            "policymaker_briefing_memo": policy_memo
        }

    def _record_audit_log(self, record: Dict[str, Any]):
        log_file = os.path.join(BASE_DIR, "memory", "runtime", "dailylog.md")
        audit_payload = {
            "ingestion": record["ingestion"],
            "demographic_context": record["demographic_context"],
            "priority_and_budget": record["priority_and_budget"],
            "checker_audit": record["checker_audit"],
        }
        input_hash = hashlib.sha256(json.dumps(audit_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        reasoning_trace = (
            f"category={record['ingestion']['detected_category']}; "
            f"baseline={record['demographic_context']['status']}; "
            f"pus={record['priority_and_budget']['priority_urgency_score']}; "
            f"checker={record['checker_audit']['status']}"
        )
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n### Execution [{record['metadata']['timestamp']}] Seal: {record['metadata']['verification_seal']}\n")
            f.write(f"- **Input/decision hash:** `{input_hash}`\n")
            f.write(f"- **Reasoning trace:** `{reasoning_trace}`\n")
            f.write(f"- **District:** {record['demographic_context']['district_name']}, {record['demographic_context']['state_province']}\n")
            f.write(f"- **Category:** {record['ingestion']['detected_category']} (Urgency: {record['priority_and_budget']['priority_urgency_score']}/100)\n")
            f.write(f"- **Capex:** ₹{record['priority_and_budget']['estimated_capex_inr']:,} INR | Beneficiaries: {record['priority_and_budget']['estimated_beneficiaries']:,}\n")
            f.write(f"- **Checker Status:** {record['checker_audit']['status']} ({record['checker_audit']['verification_hash']})\n")
            f.write("- **Authority:** Human officer approval required; this is not an automatic allocation.\n")

        # A separate, sanitized event stream powers demand-hotspot aggregation.
        # It intentionally excludes raw citizen text and all contact tokens.
        events_file = os.path.join(BASE_DIR, ".gitagent", "demand_events.jsonl")
        event = {
            "event_id": record["metadata"]["verification_seal"],
            "timestamp": record["metadata"]["timestamp"],
            "district_id": record["demographic_context"]["district_id"],
            "district_name": record["demographic_context"]["district_name"],
            "category": record["ingestion"]["detected_category"],
            "channel": record["ingestion"]["channel"],
            "demand_volume": record["priority_and_budget"].get("demand_volume", 0),
            "priority_urgency_score": record["priority_and_budget"]["priority_urgency_score"],
            "estimated_capex_inr": record["priority_and_budget"]["estimated_capex_inr"],
            "checker_status": record["checker_audit"]["status"],
            "coordinates": record["demographic_context"].get("coordinates"),
        }
        with open(events_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

if __name__ == "__main__":
    engine = JanSetuEngine()
    test_demand = "नमस्ते, कटिहार बरारी में 5 दिन से पाइपलाइन फटी है, पानी नहीं आ रहा है, फोन 9876543210"
    res = engine.process_citizen_demand(test_demand, location_hint="Katihar")
    print(json.dumps(res, indent=2, ensure_ascii=True))
