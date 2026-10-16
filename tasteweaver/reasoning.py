# -*- coding: utf-8 -*-
"""Dual brain: OpenAI-compatible LLM + deterministic offline fallback.

The LLM is treated as an *untrusted* input source: every field it returns is
validated/coerced before it reaches the planner, and anything unusable falls
back to the deterministic offline parse rather than crashing the loop.
"""
from __future__ import annotations
import os
import re
import json
import urllib.request
import urllib.error

from .planning import OCCASION_DOMAINS, symbol

ANCHOR_WORDS = ["jazz", "sci-fi", "romantic", "classical", "streetwear",
                "vegan", "anime", "hiking", "coffee", "electronic"]

LOCALES = ["shanghai", "beijing", "hangzhou", "shenzhen", "guangzhou",
           "tokyo", "paris", "london", "new york"]

VALID_OCCASIONS = set(OCCASION_DOMAINS)

_CNY_WORDS = ("rmb", "cny", "yuan", "\u5143", "\u00a5")
# symbol-prefix ("$50", "\u00a550") and word-suffix ("400 RMB", "50 dollars")
_BUDGET_SYMBOL_RE = re.compile(r"([\$\u00a5\uffe5])\s*(\d[\d,]*)")
_BUDGET_RE = re.compile(
    r"(\d[\d,]*)\s*(rmb|cny|yuan|\u5143|\u00a5|\$|dollars?|usd|bucks?)",
    re.IGNORECASE)
_CNY_IN_TEXT = re.compile(r"(rmb|cny|yuan|\u5143|\u00a5)", re.IGNORECASE)


def detect_currency(text):
    """CNY if the request mentions a yuan-ish unit, else USD."""
    return "CNY" if _CNY_IN_TEXT.search(text or "") else "USD"


def _as_list(v):
    """Coerce an untrusted value into a clean list of lowercase strings."""
    if isinstance(v, list):
        return [str(x).strip().lower() for x in v if str(x).strip()]
    if isinstance(v, str) and v.strip():
        return [v.strip().lower()]
    return []


def _as_num(v):
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        m = re.search(r"(\d[\d,]*(?:\.\d+)?)", v)
        if m:
            return float(m.group(1).replace(",", ""))
    return None


def _as_str(v):
    if isinstance(v, str) and v.strip():
        return v.strip()
    return None


class OfflineBrain:
    """Deterministic intent parser + explainer (no network, no key)."""

    name = "offline"

    def parse_intent(self, request):
        text = request.lower()
        budget, currency = None, detect_currency(text)
        m = _BUDGET_SYMBOL_RE.search(request)  # "$50" / "\u00a550" (symbol first)
        if m:
            budget = float(m.group(2).replace(",", ""))
            currency = "CNY" if m.group(1) in ("\u00a5", "\uffe5") else "USD"
        else:
            m = _BUDGET_RE.search(text)
            if m:
                budget = float(m.group(1).replace(",", ""))
                currency = "CNY" if m.group(2).lower() in _CNY_WORDS else "USD"
        locale = next((loc for loc in LOCALES if loc in text), None)
        if "date" in text or "night" in text or "romantic" in text:
            occasion = "date-night"
        elif "gift" in text:
            occasion = "gift"
        elif any(w in text for w in ("dinner", "meal", "eat", "lunch")):
            occasion = "dinner"
        elif "hike" in text or "outing" in text or "trip" in text or "walk" in text:
            occasion = "outing"
        else:
            occasion = "evening"
        excluded = []
        if any(p in text for p in ("no spicy", "hates spicy", "not spicy",
                                   "avoid spicy", "hate spicy", "without spicy")):
            excluded += ["spicy", "sichuan", "hot"]
        anchors = [a for a in ANCHOR_WORDS if a in text]
        for m in re.finditer(r"(?:loves?|into|likes?|fan of|enjoy)\s+([a-z][a-z\- ]{2,24})", text):
            a = m.group(1).strip()
            if a and a not in anchors:
                anchors.append(a)
        seen, uniq = set(), []
        for a in anchors:
            if a not in seen:
                seen.add(a)
                uniq.append(a)
        return {"occasion": occasion, "locale": locale, "budget": budget,
                "currency": currency, "anchors": uniq, "excluded": excluded,
                "raw": request}

    def explain(self, plan, intent):
        if not plan["picks"]:
            return ("I could not find picks that fit your taste and constraints. "
                    "Try loosening the budget or removing exclusions.")
        lines = []
        for c in plan["picks"]:
            e, aff = c["entity"], c["affinity"]
            matched = ", ".join(aff["matched_tags"]) or "general fit"
            price = " ~%s%g" % (symbol(e.get("currency")), e["price"]) if e.get("price") else ""
            fit = c.get("occasion_fit", 0)
            fit_note = ("; fits %s" % plan.get("occasion", "evening")) if fit > 0 else ""
            lines.append("- %s (%s): grounded on your taste via %s "
                         "(affinity %.2f, rating %.1f%s%s)."
                         % (e["name"], e["domain"], matched, aff["score"],
                            e["rating"], price, fit_note))
        return "\n".join(lines)


class LLMBrain:
    """OpenAI-compatible brain; falls back to OfflineBrain on any failure."""

    def __init__(self, base_url, api_key, model):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.name = "llm"
        self._offline = OfflineBrain()

    def _chat(self, system, user, timeout=20):
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": 0.2,
        }).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/chat/completions", data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + self.api_key})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    def parse_intent(self, request):
        try:
            sys = ("Parse the request into JSON with keys: occasion (one of "
                   "date-night/dinner/gift/evening/outing), locale (or null), "
                   "budget (number or null), currency (USD or CNY), "
                   "anchors (list of taste keywords), "
                   "excluded (list of tags to avoid). Return ONLY JSON.")
            raw = self._chat(sys, request)
            raw = raw[raw.find("{"):raw.rfind("}") + 1]
            parsed = json.loads(raw)
            occasion = str(parsed.get("occasion") or "").lower()
            out = {"occasion": occasion if occasion in VALID_OCCASIONS else "evening",
                   "locale": _as_str(parsed.get("locale")),
                   "budget": _as_num(parsed.get("budget")),
                   "currency": self._currency(parsed, request),
                   "anchors": _as_list(parsed.get("anchors")),
                   "excluded": _as_list(parsed.get("excluded")),
                   "raw": request}
            # An LLM that lost the anchors would silently produce an ungrounded
            # plan; salvage them from the deterministic parser instead.
            if not out["anchors"]:
                out["anchors"] = self._offline.parse_intent(request)["anchors"]
            return out
        except Exception:
            return self._offline.parse_intent(request)

    @staticmethod
    def _currency(parsed, request):
        c = str(parsed.get("currency") or "").upper()
        if c == "RMB":
            c = "CNY"
        if c in ("USD", "CNY"):
            return c
        return detect_currency(request)

    def explain(self, plan, intent):
        try:
            picks = [{"name": c["entity"]["name"], "domain": c["entity"]["domain"],
                      "matched_tags": c["affinity"]["matched_tags"],
                      "affinity": c["affinity"]["score"]} for c in plan["picks"]]
            sys = ("Write a short, warm justification for each recommendation, "
                   "citing the matched taste tags. One bullet per pick. Plain English.")
            return self._chat(sys, "Request: %s\nPicks: %s" % (intent.get("raw", ""),
                              json.dumps(picks, ensure_ascii=False)))
        except Exception:
            return self._offline.explain(plan, intent)


def get_brain():
    base = os.environ.get("TASTEWEAVER_LLM_BASE_URL", "")
    key = os.environ.get("TASTEWEAVER_LLM_API_KEY", "")
    if base and key:
        try:
            return LLMBrain(base, key, os.environ.get("TASTEWEAVER_LLM_MODEL", "mimo-v2-flash"))
        except Exception:
            pass
    return OfflineBrain()
