# -*- coding: utf-8 -*-
"""Stdlib web console (reads PORT for hosted demos)."""
from __future__ import annotations
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from .agent import Agent
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


def serve(graph, port=None):
    port = int(port or os.environ.get("PORT", 8790))
    agent = Agent(graph, __import__("tasteweaver.reasoning", fromlist=["get_brain"]).get_brain())

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body):
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        def do_GET(self):
            self._send(200, FORM)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0"))
            data = parse_qs(self.rfile.read(n).decode("utf-8"))
            req = (data.get("request", [""])[0] or "").strip()
            if req:
                self._send(200, receipts.html_receipt(agent.weave(req)))
            else:
                self._send(200, FORM)

        def log_message(self, *a):
            pass

    print("TasteWeaver web console on http://0.0.0.0:%d" % port)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
