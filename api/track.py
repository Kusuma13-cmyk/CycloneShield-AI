"""
CycloneShield AI — Vercel Serverless Function: /api/track
Returns cyclone track data as JSON.

GET /api/track?storm_id=BOB2024_01
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
        storm_id = params.get("storm_id", [""])[0]

        try:
            from tools.cyclone_tools import load_sample_track_data, cyclone_track_lookup_tool

            if storm_id:
                result = cyclone_track_lookup_tool(storm_id)
                track = result.get("data", [])
                source = result.get("data_source", "sample")
            else:
                track = load_sample_track_data()
                source = "sample"

            self._send({"track": track, "count": len(track), "source": source}, 200)
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
