# -*- coding: utf-8 -*-
"""Offline assertion suite for TasteWeaver. Run: python eval.py

Everything runs offline: the live Qloo client is exercised through an injected
fake transport (no network, no key, no sleeping).
"""
import os
import sys
import json
import time
import threading
import subprocess
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from tasteweaver.mock_qloo import MockQloo
from tasteweaver.reasoning import OfflineBrain, LLMBrain, detect_currency
from tasteweaver.profile import build_profile
from tasteweaver.planning import (ground_and_plan, to_usd, from_usd, occasion_fit,
                                  CNY_PER_USD, OCCASION_DOMAINS)
from tasteweaver.agent import Agent
from tasteweaver import receipts
from tasteweaver.qloo import QlooClient

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


def section(title):
    print("\n--- %s" % title)


# ---------------------------------------------------------------- fakes
class FakeResp:
    def __init__(self, payload):
        self._b = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def make_opener(script):
    """Opener that replays a script of responses/exceptions."""
    st = {"i": 0}

    def opener(req, timeout=None):
        item = script[st["i"]] if st["i"] < len(script) else script[-1]
        st["i"] += 1
        if isinstance(item, Exception):
            raise item
        return item

    return opener


def http_error(code, headers=None):
    return urllib.error.HTTPError("https://hackathon.api.qloo.com/x", code,
                                  "err", headers or {}, None)


TAGS_PAYLOAD = {"tags": [{"name": "jazz"}, {"name": "live-music"}]}
SEARCH_PAYLOAD = {"entities": [{"entity": {"id": "s1", "name": "Blue Note",
                                           "tags": [{"name": "jazz"}],
                                           "type": "urn:entity:place"},
                                "affinity": 0.8}]}
INSIGHTS_PAYLOAD = {"entities": [
    {"entity": {"id": "x1", "name": "Blue Note Cellar",
                "tags": [{"name": "jazz"}, {"name": "date-night"}],
                "type": "urn:entity:place"}, "affinity": 0.91}]}


def main():
    g = MockQloo()
    b = OfflineBrain()

    # ---------------------------------------------------------- A. intent
    section("A. intent parsing (offline brain)")

    it = b.parse_intent("Plan a jazz date night in Shanghai under 400 RMB - she loves jazz, he hates spicy food")
    check("parse.occasion", it["occasion"] == "date-night", it)
    check("parse.locale", it["locale"] == "shanghai", it)
    check("parse.budget", it["budget"] == 400, it)
    check("parse.currency-cny", it["currency"] == "CNY", it)
    check("parse.anchors", "jazz" in it["anchors"], it)
    check("parse.excluded", "spicy" in it["excluded"], it)

    check("parse.usd-dollars",
          b.parse_intent("dinner under 50 dollars")["currency"] == "USD")
    check("parse.usd-symbol",
          b.parse_intent("dinner under $50")["budget"] == 50)
    check("parse.cny-symbol-prefix",
          b.parse_intent("dinner under \u00a5300")["currency"] == "CNY"
          and b.parse_intent("dinner under \u00a5300")["budget"] == 300)
    check("parse.cny-yuan-symbol",
          b.parse_intent("dinner under 400 yuan")["currency"] == "CNY")
    check("parse.cny-hanzi",
          b.parse_intent("dinner under 400\u5143")["currency"] == "CNY")
    check("parse.no-budget",
          b.parse_intent("a vegan dinner with classical music")["budget"] is None)
    check("parse.thousands-comma",
          b.parse_intent("gift under 1,200 RMB")["budget"] == 1200)
    check("detect-currency.default-usd", detect_currency("movie night") == "USD")
    check("detect-currency.rmb", detect_currency("under 300 rmb") == "CNY")

    # ---------------------------------------------------------- B. graph
    section("B. taste graph (mock)")

    exp = g.expand_anchor("jazz")
    check("expand.tags", "jazz" in exp["tags"], exp)
    check("expand.related", "d_jazz_lounge" in exp["related_entities"], exp)

    prof = build_profile(["jazz"], g)
    check("profile.tags", "jazz" in prof["tags"], prof)

    res = g.search("dining", prof["tags"], locale="shanghai")
    check("search.top", bool(res) and res[0]["entity"]["id"] == "d_jazz_lounge", res[:1])

    aff = g.affinity("m_kind_of_blue", prof["tags"])
    check("affinity.jazz", aff["score"] > 0 and "jazz" in aff["matched_tags"], aff)
    check("affinity.unknown-entity-zero",
          g.affinity("nope", prof["tags"])["score"] == 0.0)

    # ---------------------------------------------------------- C. planning
    section("C. planning: currency, budget, occasion fit, trail")

    check("fx.cny-to-usd", to_usd(400, "CNY") == 55.56, to_usd(400, "CNY"))
    check("fx.usd-identity", to_usd(50, "USD") == 50.0)
    check("fx.roundtrip", abs(from_usd(to_usd(400, "CNY"), "CNY") - 400) < 0.05)
    check("fx.rate-disclosed", CNY_PER_USD == 7.2)
    check("fit.full", occasion_fit(["romance", "intimate"], "date-night") == 0.4)
    check("fit.none", occasion_fit(["spicy"], "date-night") == 0.0)
    check("fit.unknown-occasion", occasion_fit(["x"], "party") == 0.0)

    intent = {"occasion": "date-night", "locale": "shanghai", "budget": 400,
              "currency": "CNY", "anchors": ["jazz"], "excluded": ["spicy", "sichuan", "hot"]}
    plan = ground_and_plan(intent, build_profile(["jazz"], g), g)
    check("plan.budget", plan["spent"] <= plan["budget_usd"], plan["spent"])
    check("plan.no-hotpot", all(c["entity"]["id"] != "d_sichuan" for c in plan["picks"]),
          [c["entity"]["id"] for c in plan["picks"]])
    check("plan.one-per-domain",
          len(plan["picks"]) == len({c["entity"]["domain"] for c in plan["picks"]}))
    check("plan.nonempty", len(plan["picks"]) >= 2, len(plan["picks"]))
    check("plan.cny-entity-normalized",
          any(c["entity"]["id"] == "d_jazz_lounge" and c["price_usd"] == 52.78
              for c in plan["considered"]),
          [(c["entity"]["id"], c.get("price_usd")) for c in plan["considered"]])
    check("plan.spent-display-currency",
          abs(plan["spent_display"] - 380) < 0.05, plan["spent_display"])
    check("plan.budget-normalized", plan["budget_usd"] == 55.56, plan["budget_usd"])
    check("plan.occasion-fit-recorded",
          any(c["entity"]["id"] == "d_jazz_lounge" and c["occasion_fit"] > 0
              for c in plan["considered"]))
    check("plan.considered-trail", len(plan["considered"]) >= len(plan["picks"]))

    # a CNY budget must not authorize a USD-sized spend
    tight = dict(intent, budget=100)
    tplan = ground_and_plan(tight, build_profile(["jazz"], g), g)
    check("plan.cny-budget-enforced",
          all(c["entity"]["id"] != "d_jazz_lounge" for c in tplan["picks"]),
          [c["entity"]["id"] for c in tplan["picks"]])
    check("plan.over-budget-marked",
          any(c.get("dropped") == "over-budget" for c in tplan["considered"]))

    # budget of exactly zero is a real constraint, not "no budget"
    zero = {"occasion": "evening", "locale": "shanghai", "budget": 0,
            "currency": "USD", "anchors": ["jazz"], "excluded": []}
    zplan = ground_and_plan(zero, build_profile(["jazz"], g), g)
    check("plan.zero-budget-honored",
          all((c["entity"].get("price") or 0) == 0 for c in zplan["picks"]),
          [(c["entity"]["id"], c["entity"].get("price")) for c in zplan["picks"]])

    # excluded tags are marked in the trail, not silently dropped
    excl = {"occasion": "date-night", "locale": "shanghai", "budget": None,
            "currency": "USD", "anchors": ["jazz", "spicy"], "excluded": ["spicy"]}
    eplan = ground_and_plan(excl, build_profile(["jazz", "spicy"], g), g)
    check("plan.excluded-marked",
          any(str(c.get("dropped", "")).startswith("excluded-tag")
              for c in eplan["considered"]))
    check("plan.excluded-not-picked",
          all(c["entity"]["id"] != "d_sichuan" for c in eplan["picks"]))

    empty = MockQloo(entities=[], anchor_tags={})
    empty_plan = ground_and_plan(intent, build_profile(["jazz"], empty), empty)
    check("qloo-central.no-graph-no-picks", len(empty_plan["picks"]) == 0, empty_plan["picks"])

    # occasion fit must outrank raw affinity + rating (the "coherent weave")
    e1 = {"id": "e1", "name": "Loud Bar", "domain": "dining",
          "tags": ["jazz"], "locale": "shanghai", "price": 10, "rating": 4.9,
          "source": "qloo://e1", "currency": "CNY"}
    e2 = {"id": "e2", "name": "Candlelit Bistro", "domain": "dining",
          "tags": ["jazz", "romance", "intimate"], "locale": "shanghai",
          "price": 10, "rating": 4.0, "source": "qloo://e2", "currency": "CNY"}
    fg = MockQloo(entities=[e1, e2], anchor_tags={"jazz": ["jazz"]})
    fintent = {"occasion": "date-night", "locale": "shanghai", "budget": None,
               "currency": "USD", "anchors": ["jazz"], "excluded": []}
    fplan = ground_and_plan(fintent, build_profile(["jazz"], fg), fg)
    check("plan.fit-outranks-affinity",
          fplan["picks"] and fplan["picks"][0]["entity"]["id"] == "e2",
          [c["entity"]["id"] for c in fplan["picks"]])
    tintent = dict(fintent, occasion="outing")  # neither entity fits an outing
    tplan2 = ground_and_plan(tintent, build_profile(["jazz"], fg), fg)
    check("plan.rating-tiebreak-without-fit",
          tplan2["picks"] and tplan2["picks"][0]["entity"]["id"] == "e1",
          [c["entity"]["id"] for c in tplan2["picks"]])

    # ---------------------------------------------------------- D. LLM brain
    section("D. LLM brain: untrusted output validation")

    lb = LLMBrain("http://127.0.0.1:59999", "x", "m")
    it2 = lb.parse_intent("jazz dinner in Shanghai under 200 RMB")
    check("llm.fallback", it2["locale"] == "shanghai"
          and it2["occasion"] in ("dinner", "date-night", "evening"), it2)

    lb._chat = lambda system, user: json.dumps({
        "occasion": "partyy", "locale": "Shanghai", "budget": "400",
        "currency": "rmb", "anchors": "jazz", "excluded": None})
    it3 = lb.parse_intent("jazz date night in Shanghai under 400 RMB")
    check("llm.invalid-occasion-defaulted", it3["occasion"] == "evening", it3)
    check("llm.budget-string-coerced", it3["budget"] == 400.0, it3)
    check("llm.currency-normalized", it3["currency"] == "CNY", it3)
    check("llm.anchors-string-coerced", it3["anchors"] == ["jazz"], it3)
    check("llm.excluded-null-safe", it3["excluded"] == [], it3)

    lb._chat = lambda system, user: json.dumps({"anchors": [], "occasion": "gift"})
    it4 = lb.parse_intent("gift ideas for a streetwear fan")
    check("llm.empty-anchors-salvaged", "streetwear" in it4["anchors"], it4)

    def boom(system, user):
        raise RuntimeError("llm down")

    lb._chat = boom
    it5 = lb.parse_intent("gift ideas for a streetwear fan in Shanghai under 500 RMB")
    check("llm.hard-failure-offline", it5["occasion"] == "gift"
          and it5["budget"] == 500 and it5["currency"] == "CNY", it5)

    # ---------------------------------------------------------- E. live client
    section("E. live Qloo client: retry, cache, failure (fake transport)")

    delays = []
    g1 = QlooClient(api_key="k", opener=make_opener(
        [http_error(429), FakeResp(TAGS_PAYLOAD), FakeResp(SEARCH_PAYLOAD)]),
        sleep=delays.append)
    r1 = g1.expand_anchor("jazz")
    check("qloo.retry-then-success", "jazz" in r1["tags"], r1)
    check("qloo.retry-counted", g1.retries == 1, g1.retries)
    check("qloo.backoff-exponential", delays == [1.0], delays)

    delays2 = []
    g2 = QlooClient(api_key="k", opener=make_opener(
        [http_error(429, {"Retry-After": "2"}), FakeResp(TAGS_PAYLOAD),
         FakeResp(SEARCH_PAYLOAD)]),
        sleep=delays2.append)
    g2.expand_anchor("jazz")
    check("qloo.retry-after-honored", delays2 == [2.0], delays2)

    delays3 = []
    g3 = QlooClient(api_key="k", max_retries=2, opener=make_opener(
        [http_error(503), http_error(503), http_error(503), http_error(503)]),
        sleep=delays3.append)
    try:
        g3._get("/v2/tags", {"query": "jazz"})
        raised = False
    except urllib.error.HTTPError:
        raised = True
    check("qloo.retry-exhausted-raises", raised)
    check("qloo.exhausted-attempts", g3.retries == 2 and delays3 == [1.0, 2.0],
          (g3.retries, delays3))

    delays4 = []
    g4 = QlooClient(api_key="k", opener=make_opener([http_error(401)]),
                    sleep=delays4.append)
    try:
        g4._get("/v2/tags", {"query": "jazz"})
        raised4 = False
    except urllib.error.HTTPError:
        raised4 = True
    check("qloo.auth-error-no-retry", raised4 and g4.retries == 0 and not delays4)

    # a dead network degrades the anchor expansion instead of crashing the loop
    g6 = QlooClient(api_key="k", opener=make_opener(
        [urllib.error.URLError("boom")]))
    r6 = g6.expand_anchor("jazz")
    check("qloo.network-down-degrades", r6["tags"] == ["jazz"], r6)

    g5 = QlooClient(api_key="k", opener=make_opener(
        [FakeResp(INSIGHTS_PAYLOAD), FakeResp(INSIGHTS_PAYLOAD)]))
    s1 = g5.search("dining", ["jazz"])
    s2 = g5.search("dining", ["jazz"])
    check("qloo.insights-cached", g5.calls == 1 and s1 and s2, g5.calls)
    check("qloo.affinity-parsed",
          g5.affinity("x1", ["jazz"])["score"] == 0.91)
    check("qloo.unknown-affinity-zero",
          g5.affinity("nope", ["jazz"])["score"] == 0.0)

    # ---------------------------------------------------------- F. agent+receipts
    section("F. agent loop and receipts")

    agent = Agent(g, b)
    r = agent.weave("Plan a jazz-themed date night in Shanghai under 400 RMB - she loves jazz, he hates spicy food")
    check("weave.picks", len(r["plan"]["picks"]) >= 2, len(r["plan"]["picks"]))
    check("weave.explain", ("affinity" in r["explanation"].lower())
          or ("grounded" in r["explanation"].lower()))
    check("weave.receipt", "TasteWeaver" in receipts.text_receipt(r))

    tr = receipts.text_receipt(r)
    check("receipt.currency-disclosed", "\u00a5400" in tr and "7.2" in tr)
    check("receipt.decision-trail", "Considered:" in tr)
    check("receipt.coherence-line", "Coherence:" in tr)

    hr = receipts.html_receipt(r)
    check("receipt.html.no-script", "<script" not in hr.lower())
    check("receipt.html.fit-column", "Occasion fit" in hr)

    hostile = MockQloo(entities=[{
        "id": "h1", "name": "<script>alert(1)</script>", "domain": "dining",
        "tags": ["jazz"], "locale": "shanghai", "price": 10, "rating": 5,
        "source": "qloo://h1", "currency": "CNY"}])
    hagent = Agent(hostile, b)
    hres = hagent.weave("jazz date night in Shanghai under 400 RMB")
    hhtml = receipts.html_receipt(hres)
    check("receipt.html.escapes-name",
          "&lt;script&gt;" in hhtml and "<script>alert" not in hhtml)

    empty_res = Agent(empty, b).weave("jazz date night in Shanghai")
    check("receipt.empty-plan", "no picks" in receipts.text_receipt(empty_res).lower())

    # ---------------------------------------------------------- G. web console
    section("G. web console (/healthz, form, POST)")

    from tasteweaver.web import make_server
    srv = make_server(MockQloo(), 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        base = "http://127.0.0.1:%d" % port
        h = urllib.request.urlopen(base + "/healthz", timeout=5)
        check("web.healthz", h.read().decode() == "ok")
        form = urllib.request.urlopen(base + "/", timeout=5).read().decode("utf-8")
        check("web.form", "TasteWeaver" in form)
        req = urllib.request.Request(
            base + "/", data=b"request=jazz+date+night+in+Shanghai+under+400+RMB",
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        page = urllib.request.urlopen(req, timeout=5).read().decode("utf-8")
        check("web.post-receipt", "TasteWeaver" in page and "Occasion fit" in page)
    finally:
        srv.shutdown()

    # ---------------------------------------------------------- H. CLI
    section("H. CLI")

    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env.pop("QLOO_API_KEY", None)
    for k in ("TASTEWEAVER_LLM_BASE_URL", "TASTEWEAVER_LLM_API_KEY"):
        env.pop(k, None)
    p = subprocess.run([sys.executable, "-m", "tasteweaver", "weave",
                        "jazz dinner in Shanghai under 200 RMB"],
                       cwd=HERE, env=env, capture_output=True, timeout=60)
    check("cli.weave-rc", p.returncode == 0, p.stderr.decode("utf-8", "replace")[-200:])
    check("cli.weave-output", "TasteWeaver plan" in p.stdout.decode("utf-8", "replace"))

    # Regression (2026-10-17): `serve` must honour the PORT env var, not a
    # hard-coded default. Render assigns a random $PORT; a fixed default
    # silently ignored it and the host returned 502 on the demo URL.
    port = 18793
    env2 = dict(env)
    env2["PORT"] = str(port)
    srv = subprocess.Popen([sys.executable, "-m", "tasteweaver", "serve"],
                           cwd=HERE, env=env2,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ok = False
        for _ in range(20):
            time.sleep(0.3)
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/healthz" % port, timeout=2) as r:
                    ok = r.status == 200
                    break
            except Exception:
                continue
        check("cli.serve-port-env", ok, "PORT=%d was not bound" % port)
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=5)
        except Exception:
            srv.kill()

    print("\n%d passed, %d failed" % (PASS, FAIL))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
