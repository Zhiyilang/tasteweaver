# -*- coding: utf-8 -*-
"""Offline assertion suite for TasteWeaver. Run: python eval.py"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from tasteweaver.mock_qloo import MockQloo
from tasteweaver.reasoning import OfflineBrain, LLMBrain
from tasteweaver.profile import build_profile
from tasteweaver.planning import ground_and_plan
from tasteweaver.agent import Agent
from tasteweaver import receipts

PASS = 0
FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("PASS  " + name)
    else:
        FAIL += 1
        print("FAIL  %s  %r" % (name, extra))


def main():
    g = MockQloo()
    b = OfflineBrain()

    it = b.parse_intent("Plan a jazz date night in Shanghai under 400 RMB - she loves jazz, he hates spicy food")
    check("parse.occasion", it["occasion"] == "date-night", it)
    check("parse.locale", it["locale"] == "shanghai", it)
    check("parse.budget", it["budget"] == 400, it)
    check("parse.anchors", "jazz" in it["anchors"], it)
    check("parse.excluded", "spicy" in it["excluded"], it)

    exp = g.expand_anchor("jazz")
    check("expand.tags", "jazz" in exp["tags"], exp)
    check("expand.related", "d_jazz_lounge" in exp["related_entities"], exp)

    prof = build_profile(["jazz"], g)
    check("profile.tags", "jazz" in prof["tags"], prof)

    res = g.search("dining", prof["tags"], locale="shanghai")
    check("search.top", bool(res) and res[0]["entity"]["id"] == "d_jazz_lounge", res[:1])

    aff = g.affinity("m_kind_of_blue", prof["tags"])
    check("affinity.jazz", aff["score"] > 0 and "jazz" in aff["matched_tags"], aff)

    intent = {"occasion": "date-night", "locale": "shanghai", "budget": 400,
              "anchors": ["jazz"], "excluded": ["spicy", "sichuan", "hot"]}
    plan = ground_and_plan(intent, build_profile(["jazz"], g), g)
    check("plan.budget", plan["spent"] <= 400, plan["spent"])
    check("plan.no-hotpot", all(c["entity"]["id"] != "d_sichuan" for c in plan["picks"]),
          [c["entity"]["id"] for c in plan["picks"]])
    check("plan.one-per-domain",
          len(plan["picks"]) == len({c["entity"]["domain"] for c in plan["picks"]}))
    check("plan.nonempty", len(plan["picks"]) >= 2, len(plan["picks"]))

    empty = MockQloo(entities=[], anchor_tags={})
    eplan = ground_and_plan(intent, build_profile(["jazz"], empty), empty)
    check("qloo-central.no-graph-no-picks", len(eplan["picks"]) == 0, eplan["picks"])

    lb = LLMBrain("http://127.0.0.1:59999", "x", "m")
    it2 = lb.parse_intent("jazz dinner in Shanghai under 200 RMB")
    check("llm.fallback", it2["locale"] == "shanghai"
          and it2["occasion"] in ("dinner", "date-night", "evening"), it2)

    agent = Agent(g, b)
    r = agent.weave("Plan a jazz-themed date night in Shanghai under 400 RMB - she loves jazz, he hates spicy food")
    check("weave.picks", len(r["plan"]["picks"]) >= 2, len(r["plan"]["picks"]))
    check("weave.explain", ("affinity" in r["explanation"].lower())
          or ("grounded" in r["explanation"].lower()))
    check("weave.receipt", "TasteWeaver" in receipts.text_receipt(r))

    print("\n%d passed, %d failed" % (PASS, FAIL))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
