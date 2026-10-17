# -*- coding: utf-8 -*-
"""Command line: weave / demo / serve."""
from __future__ import annotations
import argparse
import os

from .agent import Agent
from . import receipts
from .mock_qloo import MockQloo

DEMO_REQUESTS = [
    "Plan a jazz-themed date night in Shanghai under 400 RMB - she loves jazz, he hates spicy food",
    "Find me a sci-fi movie night with electronic music, no budget limit",
    "Gift ideas for a streetwear fan in Shanghai under 500 RMB",
    "A vegan dinner with classical music in Shanghai",
]


def build_graph(live):
    # Auto-enable the live Qloo Taste Graph whenever QLOO_API_KEY is present
    # (so a hosted deploy with the key set just works), else fall back to mock.
    want_live = live or bool(os.environ.get("QLOO_API_KEY"))
    if want_live:
        try:
            from .qloo import QlooClient
            g = QlooClient()
            print("[tasteweaver] live mode: Qloo Taste Graph @ %s" % g.base_url)
            return g
        except Exception as e:
            print("[tasteweaver] live Qloo unavailable (%s); using offline mock" % e)
    return MockQloo()


def safe_weave(graph, brain, request):
    """Run the agent; if the live taste graph raises, fall back to the offline
    mock so a hosted demo never 500s. Empty live results are NOT an error -- the
    agent then reports no picks rather than fabricating affinity."""
    try:
        return Agent(graph, brain).weave(request)
    except Exception as e:
        print("[tasteweaver] live graph error (%s); falling back to offline mock" % e)
        return Agent(MockQloo(), brain).weave(request)


def cmd_weave(args):
    from .reasoning import get_brain
    brain = get_brain()
    graph = build_graph(args.live)
    print(receipts.text_receipt(safe_weave(graph, brain, " ".join(args.request))))


def cmd_demo(args):
    from .reasoning import get_brain
    brain = get_brain()
    graph = build_graph(args.live)
    for i, r in enumerate(DEMO_REQUESTS, 1):
        print("=" * 60)
        print("Scenario %d: %s" % (i, r))
        print(receipts.text_receipt(safe_weave(graph, brain, r)))
        print()


def cmd_serve(args):
    from .web import serve
    serve(build_graph(args.live), args.port)


def main(argv=None):
    p = argparse.ArgumentParser(prog="tasteweaver",
                                description="Culturally-grounded planning agent (Qloo Taste Graph).")
    sub = p.add_subparsers(dest="cmd")
    pw = sub.add_parser("weave", help="weave a plan from a request")
    pw.add_argument("request", nargs="+")
    pw.add_argument("--live", action="store_true", help="use the real Qloo API")
    pw.set_defaults(func=cmd_weave)
    pd = sub.add_parser("demo", help="run scripted scenarios")
    pd.add_argument("--live", action="store_true")
    pd.set_defaults(func=cmd_demo)
    ps = sub.add_parser("serve", help="start the web console")
    # default MUST be None: web.serve() falls back to the PORT env var, which
    # is how Render/Heroku-style hosts tell us the port to bind. A hard-coded
    # default here would silently ignore $PORT and the host would 502.
    ps.add_argument("--port", type=int, default=None)
    ps.add_argument("--live", action="store_true")
    ps.set_defaults(func=cmd_serve)
    args = p.parse_args(argv)
    if not getattr(args, "func", None):
        p.print_help()
        return 1
    return args.func(args) or 0
