# -*- coding: utf-8 -*-
"""Coherent multi-domain plan assembly with taste grounding + constraints."""
from __future__ import annotations

OCCASION_DOMAINS = {
    "date-night": ["dining", "film", "music", "travel"],
    "dinner": ["dining", "music"],
    "gift": ["fashion", "music", "film"],
    "evening": ["dining", "film", "music"],
    "outing": ["travel", "dining", "music"],
}


def select_domains(occasion, profile_tags):
    return OCCASION_DOMAINS.get(occasion, ["dining", "music"])


def ground_and_plan(intent, profile, graph):
    """Search each domain, ground candidates by Qloo affinity, drop constraint
    violations, then assemble a one-per-domain plan within budget."""
    budget = intent.get("budget") or 0
    excluded = set(t.lower() for t in intent.get("excluded", []))
    locale = intent.get("locale")
    tags = profile.get("tags", set())
    domains = select_domains(intent.get("occasion", "evening"), tags)

    candidates = []
    for domain in domains:
        for c in graph.search(domain, tags, locale=locale, limit=6):
            ent = c["entity"]
            ent_tags = set(t.lower() for t in ent["tags"])
            if ent_tags & excluded:
                c["dropped"] = "excluded-tag:%s" % ",".join(sorted(ent_tags & excluded))
                candidates.append(c)
                continue
            aff = graph.affinity(ent["id"], tags)
            c["affinity"] = aff
            if aff["score"] <= 0:
                c["dropped"] = "no-cultural-fit"
                candidates.append(c)
                continue
            candidates.append(c)

    candidates.sort(key=lambda c: (c["affinity"]["score"], c["entity"]["rating"]), reverse=True)

    plan, spent, chosen = [], 0.0, set()
    for c in candidates:
        if "dropped" in c:
            continue
        d = c["entity"]["domain"]
        if d in chosen:
            continue
        price = c["entity"].get("price", 0) or 0
        if budget and price and (spent + price) > budget:
            c["dropped"] = "over-budget"
            continue
        spent += price
        chosen.add(d)
        plan.append(c)

    return {"picks": plan, "spent": round(spent, 2), "budget": budget,
            "domains": sorted(chosen), "considered": candidates}
