"""
CycloneShield AI — Vercel Serverless Function: /api/weather
Returns weather data (sample or live) as JSON.

GET /api/weather?live=false
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        use_live = params.get("live", ["false"])[0].lower() == "true"

        try:
            if use_live:
                from tools.weather_tools import load_live_weather_data
                location = params.get("location", ["Bay of Bengal"])[0]
                data = load_live_weather_data(location)
                if not data:
                    from tools.weather_tools import load_sample_weather_data
                    data = load_sample_weather_data()
                    source = "sample_fallback"
                else:
                    source = "live"
            else:
                from tools.weather_tools import load_sample_weather_data
                data = load_sample_weather_data()
                source = "sample"

            self._send({"readings": data, "count": len(data), "source": source}, 200)
        except Exception as exc:
            self._send({"error": str(exc)}, 500)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send(self, body: dict, status: int = 200):
        data = json.dumps(body, default=str).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass
