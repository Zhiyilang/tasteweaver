# -*- coding: utf-8 -*-
"""Qloo Taste Graph REST client (live mode). Mirrors the MockQloo interface.

Wired to the Qloo Agentic Hackathon spec:
  - Base URL: https://hackathon.api.qloo.com  (hackathon keys ONLY work here)
  - Auth:     X-Api-Key: <hackathon key>
  - /v2/tags      -> expand an interest/cuisine/genre keyword into taste tags
  - /search       -> look up entity IDs by name
  - /v2/insights  -> recommendations/insights (the main endpoint); takes
                     filter.type + signal.interests.tags / signal.interests.entities
  - Do NOT use /recs or /recommendations (legacy, unsupported).

Exact /v2/insights request/response shapes should be confirmed against the
"Insights API Deep Dive" once a live key is in hand; parsing below is defensive.
Any failure raises so the caller falls back to the offline mock -- the agent
never fabricates affinity. (Private in-memory caching is allowed; we never
persist Qloo data into the public repo.)
"""
from __future__ import annotations
import os
import json
import urllib.request
import urllib.error
from urllib.parse import urlencode

HACKATHON_BASE = "https://hackathon.api.qloo.com"

# our planning domains -> Qloo entity types (per hackathon guide)
DOMAIN_TO_TYPE = {
    "dining": "urn:entity:place",
    "music": "urn:entity:artist",
    "film": "urn:entity:movie",
    "tv": "urn:entity:tv_show",
    "fashion": "urn:entity:brand",
    "travel": "urn:entity:destination",
    "books": "urn:entity:book",
    "games": "urn:entity:video_game",
}
TYPE_TO_DOMAIN = {v: k for k, v in DOMAIN_TO_TYPE.items()}


class QlooClient:
    name = "qloo-live"

    def __init__(self, api_key=None, base_url=None, timeout=20):
        self.api_key = api_key or os.environ.get("QLOO_API_KEY", "")
        self.base_url = (base_url or os.environ.get("QLOO_BASE_URL") or HACKATHON_BASE).rstrip("/")
        self.timeout = timeout
        self.calls = 0
        self._insights_cache = {}   # (entity_type, frozenset(tags)) -> {eid: {entity, affinity, matched_tags}}
        self._entities = {}         # eid -> normalized entity
        self._id_type = {}          # eid -> entity_type
        if not self.api_key:
            raise ValueError("QlooClient requires QLOO_API_KEY")

    # ---------- HTTP ----------
    def _get(self, path, params=None):
        url = self.base_url + path
        if params:
            url += "?" + urlencode(params)
        req = urllib.request.Request(url, method="GET", headers={
            "X-Api-Key": self.api_key, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _post(self, path, body):
        req = urllib.request.Request(self.base_url + path,
                                     data=json.dumps(body).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json",
                                              "X-Api-Key": self.api_key,
                                              "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # ---------- parsing helpers ----------
    @staticmethod
    def _list_of(d, *keys):
        """Find the first list under any of the given keys (handles nesting)."""
        if isinstance(d, list):
            return d
        if isinstance(d, dict):
            for k in keys:
                v = d.get(k)
                if isinstance(v, list):
                    return v
            for v in d.values():
                found = QlooClient._list_of(v, *keys)
                if found:
                    return found
        return []

    @staticmethod
    def _tags_of(ent):
        raw = ent.get("tags", []) or []
        out = []
        for t in raw:
            if isinstance(t, str):
                out.append(t.lower())
            elif isinstance(t, dict) and t.get("name"):
                out.append(str(t["name"]).lower())
        return out

    def _norm(self, ent, entity_type):
        eid = ent.get("id") or ent.get("entity_id")
        norm = {
            "id": eid, "name": ent.get("name") or ent.get("title") or eid,
            "domain": TYPE_TO_DOMAIN.get(entity_type, entity_type),
            "tags": self._tags_of(ent),
            "locale": ent.get("locale") or ent.get("location") or "global",
            "price": ent.get("price", 0) or 0, "rating": ent.get("rating", 0) or 0,
            "source": ent.get("url") or ("qloo://%s" % eid),
        }
        if eid:
            self._entities[eid] = norm
            self._id_type[eid] = entity_type
        return norm

    def _insights(self, entity_type, tags, limit=20):
        """POST /v2/insights for a tag signal; cache entity->affinity per (type, tags)."""
        key = (entity_type, frozenset(t.lower() for t in tags))
        if key in self._insights_cache:
            return self._insights_cache[key]
        self.calls += 1
        body = {"filter": {"type": entity_type},
                "signal": {"interests": {"tags": sorted(key[1])}},
                "take": limit}
        d = self._post("/v2/insights", body)
        ent_map = {}
        for r in self._list_of(d, "entities", "results", "recommendations"):
            ent = r.get("entity", r) if isinstance(r, dict) else {}
            norm = self._norm(ent, entity_type)
            if not norm["id"]:
                continue
            aff = r.get("affinity", r.get("score", 0)) if isinstance(r, dict) else 0
            ent_map[norm["id"]] = {
                "entity": norm,
                "affinity": float(aff or 0),
                "matched_tags": norm["tags"] or sorted(key[1]),
            }
        self._insights_cache[key] = ent_map
        return ent_map

    # ---------- MockQloo-compatible interface ----------
    def get_entity(self, entity_id):
        return self._entities.get(entity_id)

    def expand_anchor(self, anchor):
        self.calls += 1
        a = anchor.lower().strip()
        # taste tags for the keyword
        tags = []
        try:
            td = self._get("/v2/tags", {"query": a})
            for t in self._list_of(td, "tags", "results"):
                name = t.get("name") if isinstance(t, dict) else t
                if name:
                    tags.append(str(name).lower())
        except Exception:
            pass
        if not tags:
            tags = [a]
        # seed entities by name lookup
        related = []
        try:
            sd = self._get("/search", {"query": a})
            for r in self._list_of(sd, "entities", "results"):
                ent = r.get("entity", r) if isinstance(r, dict) else r
                etype = ent.get("type") or "urn:entity:place"
                norm = self._norm(ent, etype)
                if norm["id"]:
                    related.append(norm["id"])
        except Exception:
            pass
        return {"anchor": a, "tags": tags, "related_entities": related}

    def search(self, domain, tags, locale=None, limit=8):
        entity_type = DOMAIN_TO_TYPE.get(domain, domain)
        ent_map = self._insights(entity_type, tags, limit=max(limit, 20))
        out = []
        for eid, rec in ent_map.items():
            ent = rec["entity"]
            if locale and ent.get("locale") not in (locale, "global", None):
                continue
            out.append({"entity": dict(ent),
                        "matched_tags": rec["matched_tags"],
                        "score": rec["affinity"],
                        "affinity": rec["affinity"]})
        out.sort(key=lambda c: c["score"], reverse=True)
        return out[:limit]

    def affinity(self, entity_id, profile_tags):
        etype = self._id_type.get(entity_id)
        if etype:
            ent_map = self._insights(etype, profile_tags)
            if entity_id in ent_map:
                rec = ent_map[entity_id]
                return {"entity_id": entity_id, "score": rec["affinity"],
                        "matched_tags": rec["matched_tags"]}
        # fallback: matched-tag overlap from a cached entity
        ent = self._entities.get(entity_id)
        pt = set(t.lower() for t in profile_tags)
        matched = sorted(pt & set(ent["tags"])) if ent else []
        score = round(len(matched) / max(1, len(pt)), 4) if pt else 0.0
        return {"entity_id": entity_id, "score": score, "matched_tags": matched}
