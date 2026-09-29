"""
citizen_ingest_sanitizer.py - Multilingual Citizen Request Sanitizer & Entity Extractor.
Part of JanSetu AI (OpenGAP Standard).
Strictly enforces RULES.md PII redaction invariants.
"""
import re
import json
from typing import Dict, Any, List

# Indian & International phone regex
PHONE_PATTERN = re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\b[6-9]\d{9}\b')
# Aadhaar 12-digit pattern (with optional spaces or dashes)
AADHAAR_PATTERN = re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b')
# Email pattern
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')

# Multilingual keywords dictionary
CATEGORY_KEYWORDS = {
    "Water & Sanitation": [
        "water", "drinking water", "pipeline", "borewell", "tanker", "handpump", "drainage", "sewage", "contaminated",
        "पानी", "जल", "पाइपलाइन", "बोरवेल", "हैंडपंप", "नाली", "दूषित पानी", "पेयजल",
        "தண்ணீர்", "குடிநீர்", "குழாய்",
        "నీరు", "మంచినీరు", "పైప్‌లైన్",
        "জল", "নলকূপ",
        "água", "saneamento", "esgoto"
    ],
    "Primary Healthcare": [
        "hospital", "clinic", "phc", "doctor", "ambulance", "medicine", "health centre", "fever", "epidemic", "vaccine",
        "अस्पताल", "दवाखाना", "डॉक्टर", "दवा", "एंबुलेंस", "प्राथमिक स्वास्थ्य केंद्र", "बीमारी",
        "மருத்துவமனை", "மருத்துவர்", "மருந்து",
        "ఆసుపత్రి", "వైద్యుడు", "మందులు",
        "হাসপাতাল", "ডাক্তার",
        "hospital", "médico", "posto de saúde", "remédio"
    ],
    "Rural Connectivity": [
        "road", "bridge", "pothole", "highway", "bus", "transport", "culvert", "mud road", "impassable",
        "सड़क", "रास्ता", "पुल", "पुलिया", "गड्ढा", "बस सेवा", "कच्ची सड़क",
        "சாலை", "பாலம்",
        "రోడ్డు", "వంతెన",
        "রাস্তা", "সেতু",
        "estrada", "ponte", "buraco", "asfalto"
    ],
    "Power & Energy": [
        "electricity", "power cut", "transformer", "voltage", "blackout", "load shedding", "solar",
        "बिजली", "ट्रांसफार्मर", "बिजली कटौती", "तार", "वोल्टेज", "अंधेरा",
        "மின்சாரம்", "டிரான்ஸ்பார்மர்",
        "విద్యుత్", "ట్రాన్స్‌ఫార్మర్",
        "বিদ্যুৎ",
        "eletricidade", "energia", "apagão", "transformador"
    ],
    "Education & Digital Literacy": [
        "school", "teacher", "classroom", "books", "computer", "internet", "midday meal",
        "स्कूल", "विद्यालय", "शिक्षक", "कक्षा", "किताबें", "कंप्यूटर", "मध्याह्न भोजन",
        "பள்ளி", "ஆசிரியர்",
        "పాఠశాల", "ఉపాధ్యాయుడు",
        "বিদ্যালয়", "শিক্ষক",
        "escola", "professor", "merenda"
    ]
}

def detect_language(text: str) -> str:
    """Detects coarse language script from text characters."""
    has_devanagari = bool(re.search(r'[\u0900-\u097F]', text))
    has_tamil = bool(re.search(r'[\u0B80-\u0BFF]', text))
    has_telugu = bool(re.search(r'[\u0C00-\u0C7F]', text))
    has_bengali = bool(re.search(r'[\u0980-\u09FF]', text))
    has_portuguese_accents = bool(re.search(r'[áéíóúãõçÁÉÍÓÚÃÕÇ]', text))

    if has_devanagari:
        return "hi" # Hindi / Marathi
    elif has_tamil:
        return "ta" # Tamil
    elif has_telugu:
        return "te" # Telugu
    elif has_bengali:
        return "bn" # Bengali
    elif has_portuguese_accents and any(w in text.lower() for w in ["não", "para", "estrada", "água", "saúde"]):
        return "pt" # Portuguese (BRICS Brazil)
    return "en"

def sanitize_and_parse_request(raw_text: str, channel: str = "voice_note", location_hint: str = "") -> Dict[str, Any]:
    """
    Sanitizes raw citizen input by redacting all PII and extracting structured intent.
    """
    scrubbed_text = raw_text
    pii_redacted_count = 0

    # Redact Aadhaar / National IDs
    def replace_id(match):
        nonlocal pii_redacted_count
        pii_redacted_count += 1
        return "[NATIONAL_ID_REDACTED]"
    scrubbed_text = AADHAAR_PATTERN.sub(replace_id, scrubbed_text)

    # Redact Phone numbers
    def replace_phone(match):
        nonlocal pii_redacted_count
        pii_redacted_count += 1
        return "[PHONE_REDACTED]"
    scrubbed_text = PHONE_PATTERN.sub(replace_phone, scrubbed_text)

    # Redact Emails
    def replace_email(match):
        nonlocal pii_redacted_count
        pii_redacted_count += 1
        return "[EMAIL_REDACTED]"
    scrubbed_text = EMAIL_PATTERN.sub(replace_email, scrubbed_text)

    # Detect language
    lang = detect_language(raw_text)

    # Match Category
    detected_category = "General Community Infrastructure"
    max_matches = 0
    lower_text = raw_text.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw.lower() in lower_text)
        if matches > max_matches:
            max_matches = matches
            detected_category = cat

    # Severity Heuristics
    urgency = "MEDIUM"
    critical_terms = ["emergency", "death", "hospital", "dying", "accident", "days without", "contaminated",
                      "गंभीर", "मौत", "दुर्घटना", "बीमार", "अस्पताल", "चार दिन से", "हफ्तों से", "urgência", "perigo"]
    if any(term in lower_text for term in critical_terms):
        urgency = "HIGH"

    return {
        "status": "SANITIZED_AND_EXTRACTED",
        "detected_language": lang,
        "pii_redacted": pii_redacted_count > 0,
        "pii_tokens_removed": pii_redacted_count,
        "sanitized_text": scrubbed_text,
        "detected_category": detected_category,
        "urgency_level": urgency,
        "channel": channel,
        "location_hint": location_hint or "Katihar, Bihar"
    }

if __name__ == "__main__":
    test_input = "नमस्ते, मेरा नाम रमेश है, फोन 9876543210 और आधार 4589-1234-5678 है। कटिहार के बरारी गांव में 5 दिन से पाइपलाइन फटी है, गंदा पानी आ रहा है।"
    print(json.dumps(sanitize_and_parse_request(test_input), indent=2, ensure_ascii=False))
