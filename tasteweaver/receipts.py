# -*- coding: utf-8 -*-
"""Text + HTML plan receipts with the full decision trail."""
from __future__ import annotations
import html


def _esc(s):
    return html.escape(str(s))


def text_receipt(result):
    intent, plan = result["intent"], result["plan"]
    L = []
    L.append("TasteWeaver plan  (brain: %s)" % result.get("brain", "?"))
    L.append("Request : %s" % intent.get("raw", ""))
    L.append("Occasion: %s | Locale: %s | Budget: %s"
             % (intent.get("occasion"), intent.get("locale") or "-",
                intent.get("budget") or "none"))
    L.append("Anchors : %s" % (", ".join(intent.get("anchors", [])) or "-"))
    L.append("Excluded: %s" % (", ".join(intent.get("excluded", [])) or "-"))
    L.append("")
    if plan["picks"]:
        L.append("Plan (spent $%g of $%s):" % (plan["spent"], plan["budget"] or "inf"))
        for c in plan["picks"]:
            e, aff = c["entity"], c["affinity"]
            L.append("  - [%s] %s  (affinity %.2f; matched %s; rating %.1f; src %s)"
                     % (e["domain"], e["name"], aff["score"],
                        ",".join(aff["matched_tags"]) or "-", e["rating"], e["source"]))
    else:
        L.append("Plan: (no picks satisfied taste + constraints)")
    L.append("")
    L.append("Why:")
    L.append(result["explanation"])
    return "\n".join(L)


def html_receipt(result):
    intent, plan = result["intent"], result["plan"]
    rows = []
    for c in plan["picks"]:
        e, aff = c["entity"], c["affinity"]
        rows.append(
            "<tr><td>%s</td><td>%s</td><td>%.2f</td><td>%s</td><td>%.1f</td>"
            "<td><code>%s</code></td></tr>"
            % (_esc(e["domain"]), _esc(e["name"]), aff["score"],
               _esc(",".join(aff["matched_tags"]) or "-"), e["rating"], _esc(e["source"])))
    body = "\n".join(rows) or '<tr><td colspan="6">no picks</td></tr>'
    return """<!doctype html><html><head><meta charset="utf-8">
<title>TasteWeaver</title>
<style>
body{font-family:system-ui,Arial,sans-serif;margin:2rem;color:#1a1a2e}
h1{color:#2b4cdf} .meta{color:#555;margin-bottom:1rem}
table{border-collapse:collapse;width:100%%} th,td{border:1px solid #ddd;padding:.5rem;text-align:left}
th{background:#f0f3ff} .why{white-space:pre-wrap;background:#f7f8fc;padding:1rem;border-radius:8px}
</style></head><body>
<h1>TasteWeaver</h1>
<div class="meta"><b>%s</b><br>Occasion %s &middot; Locale %s &middot; Budget %s &middot; brain %s</div>
<table><tr><th>Domain</th><th>Pick</th><th>Affinity</th><th>Matched</th><th>Rating</th><th>Source</th></tr>
%s</table>
<h3>Why</h3><div class="why">%s</div>
</body></html>""" % (
        _esc(intent.get("raw", "")), _esc(intent.get("occasion")),
        _esc(intent.get("locale") or "-"), _esc(intent.get("budget") or "none"),
        _esc(result.get("brain", "?")), body, _esc(result["explanation"]))
