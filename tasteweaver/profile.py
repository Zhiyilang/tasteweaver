# -*- coding: utf-8 -*-
"""Taste anchors -> cross-domain taste profile, expanded through the taste graph."""
from __future__ import annotations


def build_profile(anchors, graph):
    """Expand each anchor via the taste graph and merge into a profile.

    Returns {"tags": set, "entities": [ids], "expansions": [...]}.
    If the graph cannot expand anchors (empty taste graph), tags/entities stay
    empty and downstream grounding produces no picks -- by design, Qloo is central.
    """
    all_tags = set()
    entities = []
    expansions = []
    for anchor in anchors or []:
        exp = graph.expand_anchor(anchor)
        expansions.append(exp)
        for t in exp.get("tags", []):
            all_tags.add(t.lower())
        for eid in exp.get("related_entities", []):
            if eid not in entities:
                entities.append(eid)
    return {"tags": all_tags, "entities": entities, "expansions": expansions}
