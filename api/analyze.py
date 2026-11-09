"""
CycloneShield AI — Vercel Serverless Function: /api/analyze
Runs the full 3-agent pipeline and returns the AnalysisSession as JSON.

POST /api/analyze
Body (JSON, optional):
  {
    "location":          "Bay of Bengal coastal India",  // default
    "provider_override": "demo" | "granite",             // default: auto
    "use_live_weather":  false                           // default: false
  }

Response (JSON):
  {
    "session_id":    "CS-...",
    "status":        "awaiting_review" | "error",
    "provider_name": "demo" | "granite",
    "data_mode":     "sample" | "live",
    "total_duration_ms": 1234.5,
    "weather_result":  { ... },
    "cyclone_result":  { ... },
    "impact_result":   { ... },
    "llm_eval":        { ... },
    "errors":          [],
    "execution_log":   []
  }
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler

# ── Add project root to path so all modules resolve ───────────────────────────
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")


def _run_pipeline(body: dict) -> tuple[dict, int]:
    """Execute the analysis pipeline and return (response_body, http_status)."""
    try:
        from orchestration.coordinator import run_full_analysis, AnalysisSession
        from dataclasses import asdict

        location = body.get("location", "Odisha and Andhra Pradesh coast, Bay of Bengal")
        provider_override = body.get("provider_override", "")
        use_live_weather = bool(body.get("use_live_weather", False))

        # Guard: only allow known overrides
        if provider_override not in ("", "demo", "granite"):
            return {"error": f"Invalid provider_override: {provider_override}"}, 400

        session: AnalysisSession = run_full_analysis(
            location=location,
            provider_override=provider_override,
            data_mode="sample",
            use_live_weather=use_live_weather,
        )

        # Serialize session to dict — dataclass has nested dicts already
        response = {
            "session_id": session.session_id,
            "start_time": session.start_time,
            "end_time": session.end_time,
            "status": session.status,
            "provider_name": session.provider_name,
            "data_mode": session.data_mode,
            "location": session.location,
            "total_duration_ms": session.total_duration_ms,
            "weather_result": session.weather_result,
            "cyclone_result": session.cyclone_result,
            "impact_result": session.impact_result,
            "llm_eval": session.llm_eval,
            "errors": session.errors,
            "execution_log": session.execution_log,
            "human_review_status": session.human_review_status,
        }
        return response, 200

    except Exception as exc:
        return {"error": str(exc), "status": "error"}, 500


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self._cors_preflight()

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            body = json.loads(raw_body or b"{}")
        except (json.JSONDecodeError, ValueError):
            self._send({"error": "Invalid JSON body"}, 400)
            return

        result, status = _run_pipeline(body)
        self._send(result, status)

    def do_GET(self):
        """GET with query params: ?provider=demo&location=..."""
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        body = {
            "provider_override": params.get("provider", [""])[0],
            "location": params.get("location", ["Odisha and Andhra Pradesh coast, Bay of Bengal"])[0],
            "use_live_weather": params.get("live", ["false"])[0].lower() == "true",
        }
        result, status = _run_pipeline(body)
        self._send(result, status)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _cors_preflight(self):
        self.send_response(204)
        self._add_cors()
        self.end_headers()

    def _add_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send(self, body: dict, status: int = 200):
        data = json.dumps(body, default=str).encode("utf-8")
        self.send_response(status)
        self._add_cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass  # Suppress default access logs in serverless env
