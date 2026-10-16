# -*- coding: utf-8 -*-
"""Coherent multi-domain plan assembly with taste grounding + constraints."""
from __future__ import annotations

# Documented demo constant. Every receipt discloses the rate actually used, so a
# reviewer can recompute any budget decision by hand.
CNY_PER_USD = 7.2

OCCASION_DOMAINS = {
    "date-night": ["dining", "film", "music", "travel"],
    "dinner": ["dining", "music"],
    "gift": ["fashion", "music", "film"],
    "evening": ["dining", "film", "music"],
    "outing": ["travel", "dining", "music"],
}

# Occasion -> tags that make a pick *fit* the occasion. This is what turns a
# per-domain "best affinity" shortlist into a coherent plan: a date night ranks
# a candlelit jazz lounge above a loud hotpot with equal affinity.
OCCASION_FIT = {
    "date-night": ["romance", "intimate", "candlelit", "date-night", "refined"],
    "dinner": ["refined", "intimate", "healthy", "vegan", "plant-based"],
    "gift": ["casual", "streetwear", "urban", "sneakers", "minimal"],
    "evening": ["late-night", "live-music", "cinematic", "dance", "electronic"],
    "outing": ["scenic", "nature", "outdoors", "hiking"],
}

FIT_WEIGHT = 0.15  # occasion fit's contribution to ranking, relative to affinity

CURRENCY_SYMBOL = {"USD": "$", "CNY": "\u00a5"}


def select_domains(occasion, profile_tags):
    return OCCASION_DOMAINS.get(occasion, ["dining", "music"])


def to_usd(amount, currency="USD"):
    """Normalize an amount to USD (internal planning currency)."""
    if amount is None:
        return None
    amt = float(amount)
    if (currency or "USD").upper() == "CNY":
        return round(amt / CNY_PER_USD, 2)
    return round(amt, 2)


def from_usd(amount_usd, currency="USD"):
    """Convert an internal USD amount back to the request's display currency."""
    if amount_usd is None:
        return None
    if (currency or "USD").upper() == "CNY":
        return round(amount_usd * CNY_PER_USD, 2)
    return round(amount_usd, 2)


def symbol(currency):
    return CURRENCY_SYMBOL.get((currency or "USD").upper(), "$")


def occasion_fit(entity_tags, occasion):
    """Fraction of the occasion's fit tags carried by the entity (0..1)."""
    fit_tags = set(OCCASION_FIT.get(occasion, []))
    if not fit_tags:
        return 0.0
    et = set(t.lower() for t in entity_tags or [])
    return round(len(et & fit_tags) / len(fit_tags), 4)


def ground_and_plan(intent, profile, graph):
    """Search each domain, ground candidates by Qloo affinity, drop constraint
    violations, then assemble a one-per-domain plan within budget.

    Budget and prices may be in different currencies; both are normalized to
    USD (rate disclosed) before any comparison, so a "400 RMB" budget can never
    silently authorize a $400 spend.
    """
    budget = intent.get("budget")
    currency = (intent.get("currency") or "USD").upper()
    budget_usd = to_usd(budget, currency) if budget is not None else None
    excluded = set(t.lower() for t in intent.get("excluded", []))
    locale = intent.get("locale")
    occasion = intent.get("occasion", "evening")
    tags = profile.get("tags", set())
    domains = select_domains(occasion, tags)

    candidates = []
    for domain in domains:
        for c in graph.search(domain, tags, locale=locale, limit=6):
            ent = c["entity"]
            ent_tags = set(t.lower() for t in ent["tags"])
            c["occasion_fit"] = occasion_fit(ent["tags"], occasion)
            ent_currency = (ent.get("currency") or "USD").upper()
            c["price_usd"] = to_usd(ent.get("price", 0) or 0, ent_currency)
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

    # candidates dropped before grounding have no affinity; rank them last
    candidates.sort(
        key=lambda c: (c.get("affinity", {}).get("score", 0.0)
                       + FIT_WEIGHT * c.get("occasion_fit", 0.0),
                       c["entity"]["rating"]),
        reverse=True)

    plan, spent_usd, chosen = [], 0.0, set()
    for c in candidates:
        if "dropped" in c:
            continue
        d = c["entity"]["domain"]
        if d in chosen:
            continue
        price_usd = c["price_usd"]
        if budget_usd is not None and price_usd and (spent_usd + price_usd) > budget_usd:
            c["dropped"] = "over-budget"
            continue
        spent_usd += price_usd
        chosen.add(d)
        plan.append(c)

    fit_hits = sum(1 for c in plan if c.get("occasion_fit", 0) > 0)
    return {"picks": plan, "spent": round(spent_usd, 2), "budget": budget,
            "currency": currency, "budget_usd": budget_usd,
            "spent_usd": round(spent_usd, 2),
            "spent_display": from_usd(spent_usd, currency),
            "domains": sorted(chosen), "occasion": occasion,
            "occasion_fit_hits": fit_hits, "considered": candidates}
