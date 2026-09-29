"""
app.py - High-Performance JanSetu AI Web Server & API Gateway.
Zero external dependencies (uses standard library http.server).
Serves the Interactive JanSetu Command Dashboard and REST API.
"""
import os
import sys
import json
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from engine import JanSetuEngine

engine = JanSetuEngine()

class JanSetuHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(BASE_DIR, "web"), **kwargs)

    def do_GET(self):
        url_parts = urllib.parse.urlparse(self.path)
        if url_parts.path == "/api/districts":
            self._handle_get_districts()
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
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body.decode('utf-8'))
            raw_text = payload.get("raw_text", "")
            channel = payload.get("channel", "voice_note")
            location_hint = payload.get("location_hint", "")
            demand_volume = int(payload.get("demand_volume", 20))

            if not raw_text:
                self._send_json({"error": "raw_text parameter is required"}, status=400)
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

    def _send_json(self, data: dict, status: int = 200):
        response_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

def run_server(port: int = 8080):
    web_dir = os.path.join(BASE_DIR, "web")
    os.makedirs(web_dir, exist_ok=True)
    server_address = ('', port)
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
