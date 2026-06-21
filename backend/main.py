#!/usr/bin/env python3
"""
AITAS Backend — main entry point.
Refactored from monolithic server.py into modular backend/ packages.

Run:  python backend/main.py [--port 8080]
"""
from __future__ import annotations

import json
import mimetypes
import re
import sys
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs, unquote, quote

# Add project root to sys.path for imports
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import ROOT_DIR, STORAGE_DIR
from backend.database import init_db


# ------------------------- HTTP Handler -------------------------

class AppHandler(BaseHTTPRequestHandler):
    server_version = "AITAS/2.0"

    def _route(self, method: str):
        """Unified routing: try API routers first, then static files."""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        body = self._read_body()
        headers = {k.lower(): v for k, v in self.headers.items()}
        query_params = {k: v for k, v in parse_qs(parsed.query).items()}

        # Inject the old interface the routers expect
        headers["Authorization"] = self.headers.get("Authorization", "")

        # Try API routers
        try:
            result = self._try_api_routers(method, path, headers, body, query_params)
            if result is not None:
                data, status = result
                self.send_json(data, status)
                return
        except Exception as exc:
            self.send_json({"error": f"服务端异常: {type(exc).__name__}: {exc}"},
                           HTTPStatus.INTERNAL_SERVER_ERROR)
            raise

        # Try static file serving
        from backend.services.file_server import try_serve_static
        try:
            if try_serve_static(path, self):
                return
        except Exception:
            pass

        # 404
        self.send_json({"error": "API 端点不存在。"}, HTTPStatus.NOT_FOUND)

    def _try_api_routers(self, method, path, headers, body, query_params):
        """Chain all API routers. Each returns (data, status) or None."""
        # Import routers lazily to avoid circular deps at module level
        from backend.routers.auth import handle_auth_routes
        from backend.routers.users import handle_user_routes
        from backend.routers.classes import handle_class_routes
        from backend.routers.coursewares import handle_courseware_routes
        from backend.routers.evaluations import handle_evaluation_routes
        from backend.routers.discussions import handle_discussion_routes
        from backend.routers.messages import handle_message_routes
        from backend.routers.ai_chat import handle_ai_chat_routes
        from backend.routers.rag import handle_rag_routes
        from backend.routers.dashboard import handle_dashboard_routes

        routers = [
            ("auth", handle_auth_routes),
            ("users", handle_user_routes),
            ("classes", handle_class_routes),
            ("coursewares", handle_courseware_routes),
            ("evaluations", handle_evaluation_routes),
            ("discussions", handle_discussion_routes),
            ("messages", handle_message_routes),
            ("ai_chat", handle_ai_chat_routes),
            ("rag", handle_rag_routes),
            ("dashboard", handle_dashboard_routes),
        ]

        for _name, router in routers:
            try:
                # Some routers need query_params
                import inspect
                sig = inspect.signature(router)
                if len(sig.parameters) >= 5:
                    result = router(path, method, headers, body, query_params)
                else:
                    result = router(path, method, headers, body)
                if result is not None:
                    return result
            except Exception as exc:
                import traceback
                traceback.print_exc()
                return {"error": f"路由 {_name} 异常: {type(exc).__name__}: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR

        return None

    def _read_body(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return b""
        return self.rfile.read(length)

    # --- HTTP methods ---

    def do_GET(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")

    def do_PUT(self):
        self._route("PUT")

    def do_DELETE(self):
        self._route("DELETE")

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.end_headers()

    def log_message(self, fmt, *args):
        pass  # suppress default console logging

    # --- Utility methods ---

    def parse_multipart_form(self) -> dict:
        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length)
        message = BytesParser(policy=default).parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
        )
        fields = {}
        for part in message.iter_parts():
            name = part.get_param("name", header="Content-Disposition")
            if not name:
                continue
            filename = part.get_filename()
            payload = part.get_payload(decode=True) or b""
            fields[name] = {
                "filename": filename,
                "data": payload,
                "value": payload.decode("utf-8", errors="ignore"),
            }
        return fields

    def send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


# ------------------------- Main -------------------------

def main():
    port = 8080
    for i, arg in enumerate(sys.argv):
        if arg in ("--port", "-p") and i + 1 < len(sys.argv):
            try:
                port = int(sys.argv[i + 1])
            except ValueError:
                pass

    print(f"[AITAS] Initializing database...")
    init_db()

    print(f"[AITAS] Starting server on http://localhost:{port}")
    server = ThreadingHTTPServer(("0.0.0.0", port), AppHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[AITAS] Shutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
