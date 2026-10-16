# -*- coding: utf-8 -*-
"""Text + HTML plan receipts with the full decision trail."""
from __future__ import annotations
import html

from .planning import CNY_PER_USD, symbol


def _esc(s):
    return html.escape(str(s))


def _budget_line(intent, plan):
    """Budget disclosure: original amount, normalized USD, and the rate used."""
    budget = plan.get("budget")
    currency = plan.get("currency", "USD")
    if budget is None:
        return "Budget : none"
    sym = symbol(currency)
    usd = plan.get("budget_usd")
    if currency == "CNY":
        return "Budget : %s%g (\u2248$%g USD @ %g)" % (sym, budget, usd, CNY_PER_USD)
    return "Budget : $%g USD" % budget


def _drop_trail(considered):
    """Summarize why candidates were dropped: {reason: count}."""
    counts = {}
    for c in considered:
        reason = c.get("dropped")
        if not reason:
            continue
        key = reason.split(":", 1)[0]
        counts[key] = counts.get(key, 0) + 1
    return counts


def text_receipt(result):
    intent, plan = result["intent"], result["plan"]
    currency = plan.get("currency", "USD")
    sym = symbol(currency)
    L = []
    L.append("TasteWeaver plan  (brain: %s)" % result.get("brain", "?"))
    L.append("Request : %s" % intent.get("raw", ""))
    L.append("Occasion: %s | Locale: %s | %s"
             % (intent.get("occasion"), intent.get("locale") or "-",
                _budget_line(intent, plan)))
    L.append("Anchors : %s" % (", ".join(intent.get("anchors", [])) or "-"))
    L.append("Excluded: %s" % (", ".join(intent.get("excluded", [])) or "-"))
    considered = plan.get("considered", [])
    drops = _drop_trail(considered)
    L.append("Considered: %d candidates, %d kept%s"
             % (len(considered), len(plan["picks"]),
                (" (dropped: %s)" % ", ".join("%s x%d" % kv for kv in sorted(drops.items())))
                if drops else ""))
    L.append("")
    if plan["picks"]:
        spent_s = "%s%g" % (sym, plan.get("spent_display", plan["spent"]))
        budget_s = ("%s%g" % (sym, plan["budget"])) if plan.get("budget") is not None else "inf"
        L.append("Plan (spent %s of %s):" % (spent_s, budget_s))
        for c in plan["picks"]:
            e, aff = c["entity"], c["affinity"]
            price = " ~%s%g" % (symbol(e.get("currency")), e["price"]) if e.get("price") else ""
            fit = c.get("occasion_fit", 0)
            fit_s = "fit %.2f" % fit if fit else "fit -"
            L.append("  - [%s] %s  (affinity %.2f; %s; matched %s; rating %.1f%s; src %s)"
                     % (e["domain"], e["name"], aff["score"], fit_s,
                        ",".join(aff["matched_tags"]) or "-", e["rating"], price, e["source"]))
        hits = plan.get("occasion_fit_hits", 0)
        L.append("")
        L.append("Coherence: %d/%d picks carry '%s' occasion tags."
                 % (hits, len(plan["picks"]), plan.get("occasion", "evening")))
    else:
        L.append("Plan: (no picks satisfied taste + constraints)")
    L.append("")
    L.append("Why:")
    L.append(result["explanation"])
    return "\n".join(L)


def html_receipt(result):
    intent, plan = result["intent"], result["plan"]
    currency = plan.get("currency", "USD")
    sym = symbol(currency)
    rows = []
    for c in plan["picks"]:
        e, aff = c["entity"], c["affinity"]
        price = " ~%s%g" % (symbol(e.get("currency")), e["price"]) if e.get("price") else ""
        rows.append(
            "<tr><td>%s</td><td>%s</td><td>%.2f</td><td>%.2f</td><td>%s</td><td>%.1f%s</td>"
            "<td><code>%s</code></td></tr>"
            % (_esc(e["domain"]), _esc(e["name"]), aff["score"],
               c.get("occasion_fit", 0.0),
               _esc(",".join(aff["matched_tags"]) or "-"), e["rating"], _esc(price),
               _esc(e["source"])))
    body = "\n".join(rows) or '<tr><td colspan="7">no picks</td></tr>'
    drops = _drop_trail(plan.get("considered", []))
    trail = ("Considered %d candidates, %d kept (dropped: %s)"
             % (len(plan.get("considered", [])), len(plan["picks"]),
                ", ".join("%s x%d" % kv for kv in sorted(drops.items())))) if drops else \
            ("Considered %d candidates, %d kept"
             % (len(plan.get("considered", [])), len(plan["picks"])))
    return """<!doctype html><html><head><meta charset="utf-8">
<title>TasteWeaver</title>
<style>
body{font-family:system-ui,Arial,sans-serif;margin:2rem;color:#1a1a2e}
h1{color:#2b4cdf} .meta{color:#555;margin-bottom:1rem}
table{border-collapse:collapse;width:100%%} th,td{border:1px solid #ddd;padding:.5rem;text-align:left}
th{background:#f0f3ff} .why{white-space:pre-wrap;background:#f7f8fc;padding:1rem;border-radius:8px}
</style></head><body>
<h1>TasteWeaver</h1>
<div class="meta"><b>%s</b><br>Occasion %s &middot; Locale %s &middot; %s &middot; brain %s<br>%s</div>
<table><tr><th>Domain</th><th>Pick</th><th>Affinity</th><th>Occasion fit</th><th>Matched</th><th>Rating</th><th>Source</th></tr>
%s</table>
<h3>Why</h3><div class="why">%s</div>
</body></html>""" % (
        _esc(intent.get("raw", "")), _esc(intent.get("occasion")),
        _esc(intent.get("locale") or "-"), _esc(_budget_line(intent, plan)),
        _esc(result.get("brain", "?")), _esc(trail), body, _esc(result["explanation"]))
