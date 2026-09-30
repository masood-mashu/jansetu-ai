"""
app.py - High-Performance JanSetu AI Web Server & API Gateway.
Zero external dependencies (uses standard library http.server).
Serves the Interactive JanSetu Command Dashboard and REST API.
"""
import os
import sys
import json
import urllib.parse
import hmac
import hashlib
from http.server import HTTPServer, SimpleHTTPRequestHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from engine import JanSetuEngine
from tools.hotspot_aggregator import aggregate_hotspots
from tools.messaging_webhook_adapter import normalize_webhook, parse_payload

engine = JanSetuEngine()
MAX_BODY_BYTES = 64 * 1024
MAX_TEXT_CHARS = 8_000
VALID_CHANNELS = {"voice_note", "sms", "whatsapp_bot", "web_portal"}

class JanSetuHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(BASE_DIR, "web"), **kwargs)

    def do_GET(self):
        url_parts = urllib.parse.urlparse(self.path)
        if url_parts.path == "/api/districts":
            self._handle_get_districts()
        elif url_parts.path == "/api/hotspots":
            self._send_json(aggregate_hotspots())
        elif url_parts.path == "/api/audit-log":
            self._handle_get_audit_log()
        elif url_parts.path == "/api/health":
            self._send_json({"status": "HEALTHY", "system": "JanSetu AI", "engine": "OpenGAP v0.1.0"})
        else:
            # Fallback to serving static files from web/
            super().do_GET()

    def do_POST(self):
        url_parts = urllib.parse.urlparse(self.path)
        if url_parts.path == "/api/process":
            self._handle_post_process()
        elif url_parts.path.startswith("/api/webhook/"):
            self._handle_post_webhook(url_parts.path.rsplit("/", 1)[-1])
        else:
            self.send_error(404, "Endpoint not found")

    def _handle_get_districts(self):
        baseline_file = os.path.join(BASE_DIR, "knowledge", "brics_districts_baseline.json")
        try:
            with open(baseline_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._send_json(data)
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def _handle_get_audit_log(self):
        log_file = os.path.join(BASE_DIR, "memory", "runtime", "dailylog.md")
        content = ""
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()
        self._send_json({"audit_log_markdown": content})

    def _handle_post_process(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
        except (TypeError, ValueError):
            self._send_json({"error": "Invalid Content-Length header"}, status=400)
            return
        if content_length < 0 or content_length > MAX_BODY_BYTES:
            self._send_json({"error": f"Request body exceeds {MAX_BODY_BYTES} bytes"}, status=413)
            return
        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body.decode('utf-8'))
            if not isinstance(payload, dict):
                self._send_json({"error": "JSON object expected"}, status=400)
                return
            raw_text = payload.get("raw_text", "")
            channel = payload.get("channel", "voice_note")
            location_hint = payload.get("location_hint", "")
            demand_volume = payload.get("demand_volume", 34)

            if not isinstance(raw_text, str) or not raw_text.strip():
                self._send_json({"error": "raw_text parameter is required"}, status=400)
                return
            if len(raw_text) > MAX_TEXT_CHARS:
                self._send_json({"error": f"raw_text exceeds {MAX_TEXT_CHARS} characters"}, status=413)
                return
            if channel not in VALID_CHANNELS:
                self._send_json({"error": "Unsupported channel"}, status=400)
                return
            if not isinstance(location_hint, str) or len(location_hint) > 200:
                self._send_json({"error": "location_hint must be a string of at most 200 characters"}, status=400)
                return
            if isinstance(demand_volume, bool) or not isinstance(demand_volume, int) or not 0 <= demand_volume <= 1_000_000:
                self._send_json({"error": "demand_volume must be an integer between 0 and 1000000"}, status=400)
                return

            result = engine.process_citizen_demand(
                raw_text=raw_text,
                channel=channel,
                location_hint=location_hint,
                demand_volume=demand_volume
            )
            self._send_json(result)
        except Exception as e:
            self._send_json({"error": f"Execution error: {str(e)}"}, status=500)

    def _read_request_body(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
        except (TypeError, ValueError):
            raise ValueError("Invalid Content-Length header")
        if content_length < 0 or content_length > MAX_BODY_BYTES:
            raise ValueError(f"Request body exceeds {MAX_BODY_BYTES} bytes")
        return self.rfile.read(content_length)

    def _webhook_signature_valid(self, body: bytes) -> bool:
        secret = os.getenv("JANSETU_WEBHOOK_SECRET")
        if not secret:
            return True  # Local demo adapter; production deployments must configure the secret.
        supplied = self.headers.get("X-JanSetu-Signature", "")
        expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(supplied, expected)

    def _handle_post_webhook(self, provider: str):
        try:
            body = self._read_request_body()
            if not self._webhook_signature_valid(body):
                self._send_json({"error": "Invalid webhook signature"}, status=401)
                return
            payload = parse_payload(body, self.headers.get("Content-Type", ""))
            normalized = normalize_webhook(provider, payload)
            result = engine.process_citizen_demand(
                raw_text=normalized["text"],
                channel=normalized["channel"],
                location_hint=normalized.get("location_hint", ""),
                demand_volume=normalized.get("demand_volume", 1),
            )
            self._send_json({
                "status": "PROCESSED",
                "provider": normalized["provider"],
                "provider_message_id": normalized.get("provider_message_id", ""),
                "sender_token": normalized["sender_token"],
                "citizen_acknowledgment": result["maker_synthesis"]["citizen_acknowledgment"],
                "verification_seal": result["metadata"]["verification_seal"],
                "checker_status": result["checker_audit"]["status"],
            })
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            self._send_json({"error": str(e)}, status=400)
        except Exception as e:
            self._send_json({"error": f"Webhook execution error: {str(e)}"}, status=500)

    def _send_json(self, data: dict, status: int = 200):
        response_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

def run_server(port: int = 8080):
    web_dir = os.path.join(BASE_DIR, "web")
    os.makedirs(web_dir, exist_ok=True)
    # The demo is intentionally local-only. Put a real authenticated gateway
    # in front of this handler before exposing it to a network.
    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, JanSetuHandler)
    print(f"=======================================================")
    print(f"[*] JanSetu AI Server Running at http://localhost:{port}")
    print(f"[*] OpenGAP Specification v0.1.0 | Google Gemini Ready")
    print(f"=======================================================\n")
    httpd.serve_forever()

if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    run_server(port)
