# -*- coding: utf-8 -*-
"""The TasteWeaver agent loop."""
from __future__ import annotations
from .profile import build_profile
from .planning import ground_and_plan


class Agent:
    """request -> PERCEIVE -> PROFILE -> SEARCH -> PLAN/GROUND -> EXPLAIN -> receipt."""

    def __init__(self, graph, brain):
        self.graph = graph
        self.brain = brain

    def weave(self, request):
        # 1. PERCEIVE
        intent = self.brain.parse_intent(request)
        # 2. PROFILE (taste graph expands anchors)
        profile = build_profile(intent.get("anchors", []), self.graph)
        # 3-5. SEARCH + GROUND + PLAN
        plan = ground_and_plan(intent, profile, self.graph)
        # 6. EXPLAIN
        explanation = self.brain.explain(plan, intent)
        return {"intent": intent, "profile": profile, "plan": plan,
                "explanation": explanation, "brain": getattr(self.brain, "name", "?")}
