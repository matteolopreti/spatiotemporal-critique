# Roadmap

The framework is mature (v4.x); everything here is gated by the project's own rules — net-improvement, prune law, and **nothing graduates from a reasoned claim to a hard guarantee before its trial**.

## Shipped in v4.12

- ✅ **Plugin-marketplace packaging** — `/plugin marketplace add matteolopreti/spatiotemporal-critique`.
- ✅ **Docs split** — README (landing) · PROTOCOL.md (spec) · CHANGELOG.md (history).

## The Trial — ✅ run (2026-07-02): results in [TRIAL.md](TRIAL.md)

First measurement is in: the protocol beat the lone critic on the same seat (recall up, invented problems down 2.6×), and the panel union hit 18/18 recall within its pre-stated invented-problem bound. The design, criteria (stated before running), caveats, and the format-robust counter owed by battery v2 all live in TRIAL.md; the harness is `trial_runner.py` + `trials/` (raw responses committed, re-scorable with `--report`).

## v5.0 — gate status after the Trial

**Gate 1 (panel value) — passed:** union recall 18/18 within the invented-problem bound (TRIAL.md, criteria pre-stated).
**Gate 2 (protocol-as-brief, the cheap falsification) — run 2026-07-02, verdict: diminishing returns.** Shipping the whole Standard preset to a non-Claude seat cut invented problems further (codex: 11 → 8) at unchanged recall — a real but modest gain that does **not** justify a new harness architecture by itself. Recall was ceilinged by battery v1, so the discriminating experiment still owes a **harder battery** (artifact-scale, subtler flaws).

**Remaining before any v5.0 build:** battery v2 (artifact-scale fixtures + a format-robust findings counter) · the orchestrator contract (what a non-Claude runner must honor: mandates, abstention, no green lights, intent stays human) · the synthesis-ownership decision (current doctrine: the reducer stays with the owner-side model) · one strong second-lineage seat with real quota headroom.

- **Multi-council review** (up to 3 vendors, blind, union-of-findings, disagreement-first, Full tier only) is *already shipped* as `--panel`; v5.0 would extend it to a full **protocol-as-harness**: a different-lineage model running the whole spatiotemporal protocol (not just a critique seat), with a third lineage as its external check.
- Standing rules carried into any v5.0: agreement — even unanimous — is corroboration, never proof; model judgment raises, only deterministic checks gate; no combined verdicts, no green lights; intent adjudication stays human.
