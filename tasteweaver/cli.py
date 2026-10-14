# -*- coding: utf-8 -*-
"""Command line: weave / demo / serve."""
from __future__ import annotations
import argparse

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
    if live:
        try:
            from .qloo import QlooClient
            g = QlooClient()
            print("[tasteweaver] live mode: Qloo Taste Graph @ %s" % g.base_url)
            return g
        except Exception as e:
            print("[tasteweaver] live Qloo unavailable (%s); using offline mock" % e)
    return MockQloo()


def cmd_weave(args):
    from .reasoning import get_brain
    agent = Agent(build_graph(args.live), get_brain())
    print(receipts.text_receipt(agent.weave(" ".join(args.request))))


def cmd_demo(args):
    from .reasoning import get_brain
    agent = Agent(build_graph(args.live), get_brain())
    for i, r in enumerate(DEMO_REQUESTS, 1):
        print("=" * 60)
        print("Scenario %d: %s" % (i, r))
        print(receipts.text_receipt(agent.weave(r)))
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
    ps.add_argument("--port", type=int, default=8790)
    ps.add_argument("--live", action="store_true")
    ps.set_defaults(func=cmd_serve)
    args = p.parse_args(argv)
    if not getattr(args, "func", None):
        p.print_help()
        return 1
    return args.func(args) or 0
