"""
engine.py - Core OpenGAP Runtime Engine for JanSetu AI.
Powers the Maker-Checker pipeline with Google Gemini 1.5 Pro / Flash.
Runs seamlessly both with live Gemini API keys and standalone deterministic mode.
"""
import os
import sys
import json
import time
import datetime
from typing import Dict, Any, Optional

# Ensure tools and agents are on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from tools.citizen_ingest_sanitizer import sanitize_and_parse_request
from tools.gis_demographic_correlator import correlate_district_demographics
from tools.priority_budget_optimizer import optimize_priority_and_budget
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
        self.model = None
        self._init_gemini()
        self._ensure_audit_dirs()

    def _init_gemini(self):
        if self.api_key and HAS_GOOGLE_GENAI:
            try:
                genai.configure(api_key=self.api_key)
                model_name = "gemini-2.0-flash"
                try:
                    self.model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=self._load_soul_and_rules()
                    )
                except Exception:
                    model_name = "gemini-1.5-pro"
                    self.model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=self._load_soul_and_rules()
                    )
                print(f"[JanSetu Engine] Connected to Google {model_name}.")
            except Exception as e:
                print(f"[JanSetu Engine] Warning: Gemini init error ({e}). Using deterministic mode.")
                self.model = None
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
        demand_volume: int = 18
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
            "priority_urgency_score": budget_res["priority_urgency_score"],
            "estimated_capex_inr": budget_res["estimated_capex_inr"],
            "estimated_beneficiaries": budget_res["estimated_beneficiaries"],
            "recommendation": budget_res["recommended_project_type"],
            "district": gis_res["district_name"]
        }
        audit_res = verify_proposal(checker_input)

        # Step 6: Package Final Response Dossier
        response_package = {
            "metadata": {
                "system": "JanSetu AI (जनसेतु)",
                "spec": "OpenGAP v0.1.0",
                "timestamp": timestamp,
                "model_engine": "google:gemini-2.0-flash" if self.model else "opengap:deterministic-engine",
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

        if self.model:
            try:
                prompt = f"""
                You are JanSetu AI, speaking to a citizen and a district magistrate.
                The citizen said: "{sanitized_text}"
                Language: {language}
                Location: {district}, {state}
                Category: {category}
                Priority Urgency Score: {pus}/100
                Recommended Project: {proj_type} (Capex: ₹{capex_lakh} Lakhs for {beneficiaries} citizens)

                Generate a JSON object with:
                1. "citizen_acknowledgment": Warm, respectful confirmation in {language} confirming that their grievance has been logged, geotagged to {district}, and escalated with priority tier {budget_data['priority_band']}.
                2. "policymaker_briefing_memo": A professional 3-sentence executive summary for the District Magistrate / Chief Secretary explaining the infrastructure deficit, demand cluster, and why this ₹{capex_lakh} Lakh investment is recommended.
                """
                response = self.model.generate_content(prompt)
                text = response.text.strip()
                # Parse JSON if enclosed in markdown
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                return json.loads(text)
            except Exception as e:
                print(f"[JanSetu Engine] Fallback to deterministic synthesis: {e}")

        # Deterministic multilingual generator
        if language == "hi":
            citizen_ack = f"नमस्ते। आपकी {category} संबंधी मांग जनसेतु प्रणाली में दर्ज कर ली गई है। आपका क्षेत्र {district}, {state} हमारे उच्च प्राथमिकता डैशबोर्ड में सम्मिलित है। आपकी समस्या को प्राथमिकता स्कोर {pus}/100 के साथ जिला प्रशासन को त्वरित कार्रवाई हेतु अग्रसारित कर दिया गया है।"
        elif language == "ta":
            citizen_ack = f"வணக்கம். உங்கள் {category} கோரிக்கை ஜனசேது அமைப்பில் பதிவு செய்யப்பட்டுள்ளது. {district}, {state} பகுதிக்கான முன்னுரிமை மதிப்பெண் {pus}/100 ஆக கணக்கிடப்பட்டு மாவட்ட நிர்வாகத்திற்கு அனுப்பப்பட்டுள்ளது."
        elif language == "te":
            citizen_ack = f"నమస్కారం. మీ {category} అభ్యర్థన జనసేతు వ్యవస్థలో విజయవంతంగా నమోదు చేయబడింది. {district}, {state} జిల్లా ప్రాధాన్యత స్కోరు {pus}/100 తో అధికారులకు సిఫార్సు చేయబడింది."
        elif language == "pt":
            citizen_ack = f"Olá. A sua solicitação de {category} foi registrada na plataforma JanSetu. O distrito de {district} recebeu uma pontuação de urgência de {pus}/100 e foi encaminhado para as autoridades competentes."
        else:
            citizen_ack = f"Greetings. Your citizen request regarding {category} in {district}, {state} has been securely registered on the JanSetu Digital Public Infrastructure platform. It has been awarded a Priority Urgency Score of {pus}/100 and routed to the public works division."

        policy_memo = (
            f"URGENT PROJECT PROPOSAL: Rapid demand spike detected in {district}, {state} (MPI Deprivation Index: {gis_data['mpi_deprivation_index']}). "
            f"JanSetu recommends immediate capital provisioning for '{proj_type}' with an estimated capex of ₹{capex_lakh} Lakhs ($ {budget_data['estimated_capex_usd']:,} USD), "
            f"directly benefiting {beneficiaries:,} citizens with an exceptional Benefit-Cost Ratio of {budget_data['benefit_cost_ratio_index']}."
        )

        return {
            "citizen_acknowledgment": citizen_ack,
            "policymaker_briefing_memo": policy_memo
        }

    def _record_audit_log(self, record: Dict[str, Any]):
        log_file = os.path.join(BASE_DIR, "memory", "runtime", "dailylog.md")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n### Execution [{record['metadata']['timestamp']}] Seal: {record['metadata']['verification_seal']}\n")
            f.write(f"- **District:** {record['demographic_context']['district_name']}, {record['demographic_context']['state_province']}\n")
            f.write(f"- **Category:** {record['ingestion']['detected_category']} (Urgency: {record['priority_and_budget']['priority_urgency_score']}/100)\n")
            f.write(f"- **Capex:** ₹{record['priority_and_budget']['estimated_capex_inr']:,} INR | Beneficiaries: {record['priority_and_budget']['estimated_beneficiaries']:,}\n")
            f.write(f"- **Checker Status:** {record['checker_audit']['status']} ({record['checker_audit']['verification_hash']})\n")

if __name__ == "__main__":
    engine = JanSetuEngine()
    test_demand = "नमस्ते, कटिहार बरारी में 5 दिन से पाइपलाइन फटी है, पानी नहीं आ रहा है, फोन 9876543210"
    res = engine.process_citizen_demand(test_demand, location_hint="Katihar")
    print(json.dumps(res, indent=2, ensure_ascii=True))
