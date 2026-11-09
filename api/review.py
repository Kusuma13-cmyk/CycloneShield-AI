"""
CycloneShield AI — Vercel Serverless Function: /api/review
Submits a human review decision for a session.

POST /api/review
Body (JSON):
  {
    "session_data":  { ... },   // full session dict from /api/analyze response
    "decision":      "approved" | "rejected",
    "reviewer":      "Duty Officer",
    "notes":         "optional notes"
  }

Response (JSON):
  {
    "human_review_status": "approved" | "rejected",
    "human_reviewer":      "...",
    "review_timestamp":    "...",
    "status":              "complete" | "rejected"
  }
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timezone

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

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
            body = json.loads(raw or b"{}")
        except (json.JSONDecodeError, ValueError):
            self._send({"error": "Invalid JSON body"}, 400)
            return

        decision = body.get("decision", "")
        reviewer = body.get("reviewer", "").strip()
        notes = body.get("notes", "")

        if decision not in ("approved", "rejected"):
            self._send({"error": "decision must be 'approved' or 'rejected'"}, 400)
            return
        if not reviewer:
            self._send({"error": "reviewer name is required"}, 400)
            return

        try:
            from orchestration.coordinator import AnalysisSession, submit_human_review

            # Reconstruct a minimal session from the POSTed session_data
            session_data = body.get("session_data", {})
            session = AnalysisSession(
                session_id=session_data.get("session_id", ""),
                status=session_data.get("status", "awaiting_review"),
                weather_result=session_data.get("weather_result", {}),
                cyclone_result=session_data.get("cyclone_result", {}),
                impact_result=session_data.get("impact_result", {}),
                provider_name=session_data.get("provider_name", "demo"),
                data_mode=session_data.get("data_mode", "sample"),
            )

            updated = submit_human_review(session, decision, reviewer=reviewer, notes=notes)

            self._send({
                "human_review_status": updated.human_review_status,
                "human_reviewer": updated.human_reviewer,
                "human_notes": updated.human_notes,
                "review_timestamp": updated.review_timestamp,
                "status": updated.status,
            }, 200)

        except Exception as exc:
            self._send({"error": str(exc)}, 500)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
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
