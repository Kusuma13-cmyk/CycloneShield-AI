"""
CycloneShield AI — Local Development Server
Serves the Python API endpoints on port 8000.
This is ONLY for local development — NOT for Vercel deployment.

Usage:
    python dev_server.py

Then in another terminal:
    cd frontend && npm run dev

The Next.js dev server at http://localhost:3000 will proxy /api/* to http://localhost:8000/api/*
"""
import sys
import os
import json
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Add project root to path
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

PORT = int(os.getenv("API_PORT", "8000"))


def _invoke_handler(vercel_handler_class, parent: BaseHTTPRequestHandler) -> None:
    """
    Invoke one verb method on a Vercel-style handler class WITHOUT triggering
    BaseHTTPRequestHandler.__init__, which would execute the request a second time.

    BaseHTTPRequestHandler.__init__ immediately calls self.handle() →
    handle_one_request() → do_GET/POST().  Constructing the class normally
    therefore runs the full pipeline before we can wire up rfile/wfile/headers,
    causing a duplicate response and connection timeouts.

    Instead we:
      1. Create a bare instance, bypassing __init__ entirely (object.__new__).
      2. Copy all necessary I/O attributes from the already-live parent handler.
      3. Call the correct verb method exactly once.
    """
    h = object.__new__(vercel_handler_class)

    # Wire I/O and request metadata from the live parent handler
    h.rfile = parent.rfile
    h.wfile = parent.wfile
    h.headers = parent.headers
    h.path = parent.path
    h.command = parent.command
    h.request_version = parent.request_version
    h.request = parent.request
    h.client_address = parent.client_address
    h.server = parent.server

    # Replicate the handful of BaseHTTPRequestHandler attributes that the
    # Vercel handler methods may read (send_response, send_header, etc. are
    # methods on the class, so they're available automatically via MRO).
    h.close_connection = True

    # BaseHTTPRequestHandler.log_request() (called by send_response) reads
    # self.requestline before delegating to self.log_message.  Without it
    # every response raises AttributeError the moment send_response() runs.
    # Reconstruct the request-line string from the already-parsed components.
    h.requestline = f"{parent.command} {parent.path} {parent.request_version}"

    try:
        cmd = parent.command
        if cmd == "GET":
            h.do_GET()
        elif cmd == "POST":
            h.do_POST()
        elif cmd == "OPTIONS":
            h.do_OPTIONS()
        else:
            parent._send({"error": f"Method not allowed: {cmd}"}, 405)
            return
        # Flush the socket write-buffer; handle_one_request() normally does
        # this after calling the verb method, but we bypass that path.
        h.wfile.flush()
    except Exception as exc:
        parent._send({"error": str(exc)}, 500)


class APIHandler(BaseHTTPRequestHandler):

    # ── Route tables ──────────────────────────────────────────────────────────

    _GET_ROUTES = {
        "/api/health":  "api.health",
        "/api/weather": "api.weather",
        "/api/track":   "api.track",
        "/api/analyze": "api.analyze",
    }

    _POST_ROUTES = {
        "/api/analyze": "api.analyze",
        "/api/review":  "api.review",
    }

    # ── HTTP verb handlers ────────────────────────────────────────────────────

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/")
        module_name = self._GET_ROUTES.get(path)
        if module_name:
            self._dispatch(module_name)
        else:
            self._send({"error": f"Unknown endpoint: {path}"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/")
        module_name = self._POST_ROUTES.get(path)
        if module_name:
            self._dispatch(module_name)
        else:
            self._send({"error": f"Unknown endpoint: {path}"}, 404)

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def _dispatch(self, module_name: str) -> None:
        """Import the Vercel API module and invoke its handler exactly once."""
        import importlib
        try:
            mod = importlib.import_module(module_name)
        except ImportError as exc:
            self._send({"error": f"Could not import {module_name}: {exc}"}, 500)
            return
        _invoke_handler(mod.handler, self)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send(self, body: dict, status: int = 200):
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print(f"[API] {self.address_string()} - {fmt % args}")


if __name__ == "__main__":
    print(f"CycloneShield AI — Local API server starting on http://localhost:{PORT}")
    print("Endpoints:")
    print("  GET  /api/health")
    print("  GET  /api/weather")
    print("  GET  /api/track")
    print("  POST /api/analyze  (also GET with ?provider=demo)")
    print("  POST /api/review")
    print()
    print("Press Ctrl+C to stop.")
    server = HTTPServer(("0.0.0.0", PORT), APIHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
