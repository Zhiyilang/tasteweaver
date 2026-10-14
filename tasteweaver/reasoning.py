# -*- coding: utf-8 -*-
"""Dual brain: OpenAI-compatible LLM + deterministic offline fallback."""
from __future__ import annotations
import os
import re
import json
import urllib.request
import urllib.error

ANCHOR_WORDS = ["jazz", "sci-fi", "romantic", "classical", "streetwear",
                "vegan", "anime", "hiking", "coffee", "electronic"]

LOCALES = ["shanghai", "beijing", "hangzhou", "shenzhen", "guangzhou",
           "tokyo", "paris", "london", "new york"]


class OfflineBrain:
    """Deterministic intent parser + explainer (no network, no key)."""

    name = "offline"

    def parse_intent(self, request):
        text = request.lower()
        budget = None
        m = re.search(r"(\d[\d,]*)\s*(?:rmb|yuan|元|\$|dollars?|usd)", text)
        if m:
            budget = float(m.group(1).replace(",", ""))
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
                "anchors": uniq, "excluded": excluded, "raw": request}

    def explain(self, plan, intent):
        if not plan["picks"]:
            return ("I could not find picks that fit your taste and constraints. "
                    "Try loosening the budget or removing exclusions.")
        lines = []
        for c in plan["picks"]:
            e, aff = c["entity"], c["affinity"]
            matched = ", ".join(aff["matched_tags"]) or "general fit"
            price = " ~$%g" % e["price"] if e.get("price") else ""
            lines.append("- %s (%s): grounded on your taste via %s "
                         "(affinity %.2f, rating %.1f%s)."
                         % (e["name"], e["domain"], matched, aff["score"],
                            e["rating"], price))
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
                   "budget (number or null), anchors (list of taste keywords), "
                   "excluded (list of tags to avoid). Return ONLY JSON.")
            raw = self._chat(sys, request)
            raw = raw[raw.find("{"):raw.rfind("}") + 1]
            parsed = json.loads(raw)
            out = {"occasion": parsed.get("occasion") or "evening",
                   "locale": parsed.get("locale"),
                   "budget": parsed.get("budget"),
                   "anchors": parsed.get("anchors") or [],
                   "excluded": parsed.get("excluded") or [],
                   "raw": request}
            return out
        except Exception:
            return self._offline.parse_intent(request)

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
