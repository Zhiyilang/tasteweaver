# -*- coding: utf-8 -*-
"""Stdlib web console (reads PORT for hosted demos)."""
from __future__ import annotations
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from .agent import Agent
from .reasoning import get_brain
from .mock_qloo import MockQloo
from . import receipts

FORM = """<!doctype html><html><head><meta charset="utf-8"><title>TasteWeaver</title>
<style>body{font-family:system-ui,Arial,sans-serif;margin:3rem;max-width:680px;color:#1a1a2e}
h1{color:#2b4cdf}input{font-size:1rem;padding:.6rem;width:70%}
button{background:#2b4cdf;color:#fff;border:0;border-radius:6px;padding:.6rem 1.1rem;font-size:1rem}
p{color:#555}</style></head><body>
<h1>TasteWeaver</h1>
<p>Describe an occasion, locale, budget and taste anchors &mdash; every pick is grounded in the Qloo taste graph.</p>
<form method="post"><input name="request" autofocus
  placeholder="Plan a jazz date night in Shanghai under 400 RMB - she loves jazz">
<button>Weave</button></form></body></html>"""


def make_server(graph, port=None):
    """Build (do not start) the console server. Port 0 = ephemeral (tests)."""
    port = int(port or os.environ.get("PORT", 8790))
    brain = get_brain()
    agent = Agent(graph, brain)

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="text/html; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        def do_GET(self):
            if self.path.split("?")[0] == "/healthz":
                self._send(200, "ok", "text/plain")
                return
            self._send(200, FORM)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0"))
            if n > 64 * 1024:  # a "request" is a sentence, not an essay
                self._send(413, "request too large", "text/plain")
                return
            data = parse_qs(self.rfile.read(n).decode("utf-8"))
            req = (data.get("request", [""])[0] or "").strip()
            if not req:
                self._send(200, FORM)
                return
            try:
                result = agent.weave(req)
            except Exception:
                result = Agent(MockQloo(), brain).weave(req)
            self._send(200, receipts.html_receipt(result))

        def log_message(self, *a):
            pass

    return ThreadingHTTPServer(("0.0.0.0", port), Handler)


def serve(graph, port=None):
    srv = make_server(graph, port)
    print("TasteWeaver web console on http://0.0.0.0:%d" % srv.server_address[1])
    srv.serve_forever()
