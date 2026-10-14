# TasteWeaver — Design & Submission Plan

## Target
- Hackathon: **Qloo Agentic Hackathon** (Devpost). Online, global, adults.
- Deadline: **2026-10-30** (some mirrors say 10-31; treat 10-30 as hard).
- Prizes: 1st $15,000 / 2nd $6,000 / 3rd $4,000.
- Judging: Technological Implementation (how well it uses Qloo), Design, Potential Impact, Quality of the Idea.

## One-liner
An AI agent that turns a few taste anchors + occasion + locale + constraints into a coherent, culturally-grounded multi-domain plan (dining / music / film / …), every pick scored by Qloo's Taste Graph and explained with evidence.

## Why Qloo is central (the differentiator)
A generic LLM would "recommend" by pattern-matching words. TasteWeaver's picks are only correct because Qloo's 250M-entity taste graph provides real affinity/relatedness. Removing Qloo must break the grounding step. We enforce this: the GROUND stage scores candidates by Qloo affinity and drops poor cultural fits; a test asserts that disabling Qloo degrades the plan (no fabricated affinity).

## Architecture (reuses PayPilot's proven pattern)
PERCEIVE → PROFILE → SEARCH(Qloo) → PLAN → GROUND(Qloo affinity) → EXPLAIN → RECEIPT
- Zero-dep Python stdlib; `urllib` for Qloo REST.
- Dual brain: OpenAI-compatible LLM (Xiaomi MiMo default) + deterministic offline brain; auto-fallback asserted in eval.
- Evidence citations: each pick cites Qloo affinity score + matched constraints.
- Mock Qloo for offline demo/tests; `--live` switches to real API.

## Submission requirements → our coverage
| Requirement | Coverage |
|---|---|
| Functional hosted demo (external) | Web console deployed publicly via sites deploy (needs Qloo key for live; mock works meanwhile) |
| Public repo w/ visible license | Zhiyilang/tasteweaver, MIT (this repo) |
| Text description | Devpost form (draft separately) |
| No demo video required | — |
| Qloo-central | Enforced by GROUND stage + a negative test |

## Open items / blockers
1. **Qloo API key + base URL** — user must fetch from <https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide> (free hackathon key). Exact REST endpoints to confirm from that guide before wiring `qloo.py` (semantic search, affinity, related entities). Build with mock + confirm endpoints once key is in hand.
2. **Devpost Join** — user joins the Qloo hackathon (already has a Devpost account from PayPal).

## Build order
1. Repo skeleton + README + LICENSE + CI (this commit).
2. `mock_qloo.py` + `profile.py` + `agent.py` minimal loop + `eval.py` (offline, green).
3. Web console + receipts.
4. `qloo.py` real client wired to confirmed endpoints; `--live`.
5. Deploy hosted demo (sites); write Devpost description; user hits Submit (or browser automation).
