"""Loopback-only web server. Uploaded data stays in process memory."""

import json
import secrets
import threading
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import urlparse

from .data import MAX_BYTES, demo_csv, parse_csv
from .metrics import evaluate
from .report import render_report

REPORTS = OrderedDict()
REPORTS_LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def respond(self, status, body, content_type, attachment=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        if attachment:
            self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        path = urlparse(self.path).path
        assets = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8")}
        if path == "/api/demo":
            self.respond(200, demo_csv(), "text/csv; charset=utf-8", "synthetic-readmission.csv")
        elif path.startswith("/reports/"):
            with REPORTS_LOCK:
                report = REPORTS.get(path)
            if report is None:
                self.respond(404, "Report expired. Export a new snapshot from the dashboard.", "text/plain")
            else:
                self.respond(200, report, "text/html; charset=utf-8", "health-model-report.html" if urlparse(self.path).query == "download=1" else None)
        elif path in assets:
            name, mime = assets[path]
            self.respond(200, files("health_model_report").joinpath("static", name).read_bytes(), mime)
        else:
            self.respond(404, "Not found", "text/plain")

    def do_POST(self):
        origin = self.headers.get("Origin")
        if origin and origin != f"http://{self.headers.get('Host')}":
            self.respond(403, '{"error":"Cross-origin requests are not allowed."}', "application/json")
            return
        if self.headers.get("Host") not in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}:
            self.respond(403, '{"error":"Use the local dashboard address."}', "application/json")
            return
        if self.path not in {"/api/evaluate", "/api/report", "/api/export"}:
            self.respond(404, '{"error":"Not found"}', "application/json")
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= MAX_BYTES * 2 + 4096:
                raise ValueError("Request is empty or too large (CSV maximum: 8 MB).")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or not isinstance(payload.get("csv"), str):
                raise ValueError("Supply a JSON object with a CSV string.")
            dataset = parse_csv(payload["csv"])
            group = payload.get("group") or None
            if group is not None and not isinstance(group, str):
                raise ValueError("Subgroup must be a column name.")
            result = evaluate(dataset, float(payload.get("threshold", 0.5)), group)
            if self.path in {"/api/report", "/api/export"}:
                report = render_report(result)
                if self.path == "/api/report":
                    self.respond(200, report, "text/html; charset=utf-8", "health-model-report.html")
                else:
                    path = f"/reports/{secrets.token_urlsafe(24)}.html"
                    with REPORTS_LOCK:
                        REPORTS[path] = report
                        while len(REPORTS) > 8:
                            REPORTS.popitem(last=False)
                    self.respond(200, json.dumps({"url": path}), "application/json")
            else:
                self.respond(200, json.dumps(result, allow_nan=False), "application/json")
        except (ValueError, TypeError, UnicodeDecodeError) as exc:
            self.respond(400, json.dumps({"error": str(exc)}), "application/json")


def serve(port=8765):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Health Model Report → http://127.0.0.1:{server.server_port}", flush=True)
    print("Data is evaluated locally. Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
