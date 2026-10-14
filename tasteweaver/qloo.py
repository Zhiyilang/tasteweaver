# -*- coding: utf-8 -*-
"""Qloo Taste Graph REST client (live mode). Mirrors the MockQloo interface.

NOTE: confirm exact endpoint paths/params against the hackathon developer guide
(https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide) before
go-live; the base URL + key come from that guide. Every method raises on failure
so the caller can fall back -- the agent never fabricates affinity.
"""
from __future__ import annotations
import os
import json
import urllib.request
import urllib.error

# CONFIRM these paths from the guide:
E_TAGS = "/v2/tags"            # anchor -> taste-tag expansion
E_SEMANTIC = "/v2/semantic/search"  # entity search by tags/keywords
E_AFFINITY = "/v2/affinity"    # entity/audience affinity to tags


class QlooClient:
    name = "qloo-live"

    def __init__(self, api_key=None, base_url=None, timeout=20):
        self.api_key = api_key or os.environ.get("QLOO_API_KEY", "")
        self.base_url = (base_url or os.environ.get("QLOO_BASE_URL", "")).rstrip("/")
        self.timeout = timeout
        self.calls = 0
        if not self.api_key or not self.base_url:
            raise ValueError("QlooClient requires QLOO_API_KEY and QLOO_BASE_URL")

    def _req(self, path, body=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            self.base_url + path, data=data,
            method="POST" if data else "GET",
            headers={"Content-Type": "application/json",
                     "X-Api-Key": self.api_key, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_entity(self, entity_id):
        return None

    def expand_anchor(self, anchor):
        self.calls += 1
        d = self._req(E_TAGS, {"entity.name": anchor})
        tags = [t.get("name", "").lower() for t in d.get("tags", []) if t.get("name")]
        return {"anchor": anchor.lower(), "tags": tags,
                "related_entities": [e.get("id") for e in d.get("entities", []) if e.get("id")]}

    def search(self, domain, tags, locale=None, limit=8):
        self.calls += 1
        body = {"filter": {"types": [domain]}, "query": {"tags": list(tags)}, "take": limit}
        d = self._req(E_SEMANTIC, body)
        out = []
        for r in d.get("results", d.get("entities", [])):
            ent = r.get("entity", r)
            out.append({
                "entity": {"id": ent.get("id"), "name": ent.get("name"), "domain": domain,
                           "tags": [t.get("name", "").lower() for t in ent.get("tags", [])],
                           "locale": ent.get("locale", locale or "global"),
                           "price": ent.get("price", 0) or 0, "rating": ent.get("rating", 0) or 0,
                           "source": ent.get("url", "qloo://%s" % ent.get("id"))},
                "matched_tags": [], "score": r.get("score", 0)})
        return out

    def affinity(self, entity_id, profile_tags):
        self.calls += 1
        d = self._req(E_AFFINITY, {"entity.id": entity_id, "tags": list(profile_tags)})
        score = float(d.get("affinity", d.get("score", 0)) or 0)
        return {"entity_id": entity_id, "score": round(score, 4),
                "matched_tags": [t.lower() for t in d.get("matched_tags", [])]}
