"""Local HTTP callback server for OAuth redirect."""

from __future__ import annotations

import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

SERVICE_HOST = "www.evernote.com"
OAUTH_PORT = 10500
CALLBACK_HOST = "localhost"


class _CallbackHandler(BaseHTTPRequestHandler):
    server: _CallbackServer  # type: ignore[assignment]

    def do_GET(self) -> None:
        if not self.path.startswith("/oauth_callback?"):
            self.send_response(404)
            self.end_headers()
            return
        self.server.callback_response = self.path
        self.send_response(200)
        self.end_headers()
        self.wfile.write(
            b"<html><body>Authentication complete."
            b" You can close this tab.</body></html>"
        )

    def log_message(self, *args: Any, **kwargs: Any) -> None:
        pass  # silence server log


class _CallbackServer(HTTPServer):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.callback_response: str = ""


def wait_for_callback() -> str:
    """Start local HTTP server and block until OAuth callback is received."""
    server = _CallbackServer((CALLBACK_HOST, OAUTH_PORT), _CallbackHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        while not server.callback_response:
            time.sleep(0.1)
    finally:
        server.shutdown()
        thread.join()
    return server.callback_response
