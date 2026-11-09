"""
CycloneShield AI — Vercel Serverless Function: /api/health
Health-check endpoint — always returns 200 with system status.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._respond()

    def do_OPTIONS(self):
        self._cors_headers()
        self.end_headers()

    def _cors_headers(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _respond(self):
        body = {
            "status": "ok",
            "service": "CycloneShield AI",
            "version": "1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": os.getenv("APP_MODE", "demo"),
            "providers": {
                "ibm_granite": bool(
                    os.getenv("IBM_GRANITE_API_KEY")
                    and os.getenv("IBM_GRANITE_PROJECT_ID")
                ),
                "openweather": bool(os.getenv("OPENWEATHER_API_KEY")),
            },
        }
        data = json.dumps(body).encode("utf-8")
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
