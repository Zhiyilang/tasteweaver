# TasteWeaver

**A culturally-grounded AI agent that weaves coherent, taste-matched plans from Qloo's Taste Graph.**

Built for the [Qloo Agentic Hackathon](https://www.qloo.com/) — *"Agents, but with taste."*

LLMs can reason and plan, but they are culturally blind: ask one what to recommend and it guesses. TasteWeaver fixes that. Give it a few taste anchors plus an occasion, a locale, and constraints, and it queries **Qloo's Taste Graph** (250M+ entities across music, film, dining, fashion, travel) to build a coherent multi-domain plan — with every pick **grounded in real cultural affinity** and **explained with evidence**.

> The thesis: a generic LLM produces plausible-sounding recommendations. TasteWeaver produces *actually good* ones, because it knows what people love — and it shows its work.

- **Qloo-central** — every recommendation is scored against the user's real taste profile; remove Qloo and the agent stops working (by design).
- **Currency-aware budgets** — "under 400 RMB" is normalized to USD (disclosed rate) before any comparison, so a yuan budget can never silently authorize a dollar-sized spend.
- **Occasion-fit coherence** — picks are ranked by taste affinity *plus* occasion fit, so a date night ranks a candlelit jazz lounge above an equally-affine loud hotpot.
- **Zero dependencies** — pure Python standard library. `pip install` nothing.
- **Dual brain** — an OpenAI-compatible LLM brain for intent/explanation, or a deterministic offline brain. LLM output is validated as untrusted input; degrades gracefully if the model is down.
- **Live-API resilience** — the Qloo client retries rate limits (429) and gateway blips with exponential backoff, honoring `Retry-After`; a dead network degrades instead of crashing the loop.
- **Evidence-cited reasoning** — each recommendation cites the affinity signals and constraints it used.
- **Offline mock mode** — the full agent loop runs against an in-process Qloo mock, so anyone can run it with zero setup; `--live` points the same code at the real Qloo API.

## The agent loop

```
request ──► PERCEIVE ──► PROFILE ──► SEARCH ──► PLAN ──► GROUND ──► EXPLAIN ──► RECEIPT
             (intent,     (taste      (Qloo       (coherent   (affinity   (why, in   (plan +
              anchors)    anchors)    taste graph multi-domain evidence)  plain EN)  sources)
```

1. **PERCEIVE** — parse the request: occasion, locale, budget, constraints (dietary, time, mood), and taste anchors ("she loves jazz", "he's into sci-fi").
2. **PROFILE** — turn anchors into a taste profile across Qloo domains.
3. **SEARCH** — query the Qloo Taste Graph for candidates in each relevant domain (dining, music, film, …), ranked with evidence.
4. **PLAN** — assemble a coherent multi-domain plan (e.g., a themed evening) that respects budget and constraints; candidates are ranked by affinity **plus occasion fit**.
5. **GROUND** — score each pick against the user's taste profile via Qloo affinity; drop anything that is a poor cultural fit.
6. **EXPLAIN** — write a plain-English justification per pick, citing affinity + constraints.
7. **RECEIPT** — a plan report (text + HTML) with the full decision trail and Qloo entity sources.

## Budgets and currencies

Requests may state a budget in either currency ("under 400 RMB", "under $50", "under 400元"). The planner normalizes every amount to USD before comparing (entities carry their own currency), and the receipt discloses exactly what happened:

```
Occasion: date-night | Locale: shanghai | Budget : ¥400 (≈$55.56 USD @ 7.2)
Plan (spent ¥380.02 of ¥400):
  - [dining] Blue Note Cellar  (affinity 0.40; fit 0.20; matched jazz,live-music; rating 4.6 ~¥380)
Coherence: 1/2 picks carry 'date-night' occasion tags.
```

A `¥400` budget therefore authorizes ~$55.56 — never $400. The exchange rate is a documented constant (`CNY_PER_USD` in `planning.py`), not a hidden magic number.

## Quick start

```bash
git clone https://github.com/Zhiyilang/tasteweaver.git
cd tasteweaver

# 1. run the test suite (offline, no keys needed)
python eval.py

# 2. run the scripted demo scenarios (mock Qloo, offline)
python -m tasteweaver demo

# 3. ask the agent something yourself (mock mode)
python -m tasteweaver weave "Plan a jazz-themed date night in Shanghai under 400 RMB - she loves jazz, he hates spicy food"

# 4. start the web console (mock mode)
python -m tasteweaver serve --port 8790
# open http://127.0.0.1:8790
```

## Connecting the real Qloo API

Mock mode is the default so anyone can run everything offline. To point the agent at the live Qloo Taste Graph:

1. Get a free API key from the Qloo hackathon developer guide: <https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide>
2. Export credentials and the API base URL given in that guide:

```bash
export QLOO_API_KEY="your-hackathon-key"
export QLOO_BASE_URL="https://<qloo-hackathon-endpoint>"
```

3. Run with `--live`:

```bash
python -m tasteweaver weave "a jazz-themed Shanghai date night under 400 RMB" --live
python -m tasteweaver serve --port 8790 --live
```

## Adding an LLM brain

Any OpenAI-compatible chat endpoint works:

```bash
export TASTEWEAVER_LLM_BASE_URL="https://token-plan-cn.xiaomimimo.com/v1"
export TASTEWEAVER_LLM_API_KEY="your-key"
export TASTEWEAVER_LLM_MODEL="mimo-v2-flash"
```

The LLM does intent parsing and justification writing. If the endpoint is unreachable or returns unusable JSON, TasteWeaver falls back to the offline brain automatically.

## Self-verification

```bash
python eval.py        # 80 assertions, offline, no keys
```

Covers: intent parsing (both currencies, both symbol styles), the taste-graph
interface, currency normalization and budget enforcement (a ¥0 budget is treated
as a real constraint, not "no budget"), occasion-fit ranking, the LLM brain's
untrusted-output validation and offline fallback, the live client's
retry/backoff/cache behavior through an injected fake transport, receipt
structure and HTML escaping, the web console (`/healthz`, form, POST), and the CLI.

## Project layout

```
tasteweaver/
├── tasteweaver/
│   ├── __init__.py
│   ├── __main__.py     # python -m tasteweaver
│   ├── qloo.py         # Qloo Taste Graph REST client (tags / search / insights, retry w/ backoff)
│   ├── mock_qloo.py    # in-process Qloo mock (offline demo + tests)
│   ├── profile.py      # taste anchors -> cross-domain taste profile
│   ├── planning.py     # coherent multi-domain plan assembly (currency, budget, occasion fit)
│   ├── reasoning.py    # LLM brain + offline brain (one interface, validated LLM output)
│   ├── agent.py        # the agent loop
│   ├── receipts.py     # text + HTML plan report with decision trail
│   ├── cli.py          # weave / demo / serve commands
│   └── web.py          # stdlib web console
├── eval.py             # assertion suite, runs offline
├── examples/
│   └── requests.txt    # example natural-language requests
├── requirements.txt    # (empty - stdlib only)
├── .env.example
├── LICENSE             # MIT
└── README.md
```

## Why an agent that recommends needs cultural grounding

A generic LLM will confidently recommend things people don't actually like. TasteWeaver assumes the opposite: **the model frames the request, Qloo grounds the taste, and evidence explains every pick.** Candidates are scored against a real taste profile, constrained by occasion/locale/budget, and each choice cites the affinity signal that justified it.

## License

MIT — see [LICENSE](LICENSE).
