# Roadmap

The framework is mature (v4.x); everything here is gated by the project's own rules — net-improvement, prune law, and **nothing graduates from a reasoned claim to a hard guarantee before its trial**.

## Shipped in v4.12

- ✅ **Plugin-marketplace packaging** — `/plugin marketplace add matteolopreti/spatiotemporal-critique`.
- ✅ **Docs split** — README (landing) · PROTOCOL.md (spec) · CHANGELOG.md (history).

## The Trial — ✅ run (2026-07-02): results in [TRIAL.md](TRIAL.md)

First measurement is in: the protocol beat the lone critic on the same seat (recall up, invented problems down 2.6×), and the panel union hit 18/18 recall within its pre-stated invented-problem bound. The design, criteria (stated before running), caveats, and the format-robust counter owed by battery v2 all live in TRIAL.md; the harness is `trial_runner.py` + `trials/` (raw responses committed, re-scorable with `--report`).

## v5.0 — gate CLOSED (2026-07-02): the harness is falsified, and that is the result

All gates ran, pre-registered, on two batteries (TRIAL.md):

- **Gate 1 (panel value) — passed twice:** union recall 18/18 (v1) and 14/14 (v2) within the invented-problem rate bound.
- **Gate 2 (fuller contracts on one seat) — negative returns:** the Standard brief and the full **protocol-as-harness** beat the plain seat contract *nowhere* — equal recall with more noise on the strong seats, and *lost* recall on the small local seat. The harness panel was strictly worse than the shipped protocol panel (25 vs 21 invented, identical recall).

**Decision: no protocol-as-harness.** The shipped design — plain probe-certified seat contracts + blind multi-vendor panel + owner-side synthesis — is the measured optimum. The version line stays 4.x until a *new mechanism* earns a major bump through its own pre-registered trial; a negative result honestly recorded is worth more than a version number. The **orchestrator contract** (PROTOCOL.md) stays as the standing spec for anyone who wants to run the protocol from another model anyway — with the empirical warning attached. Synthesis ownership stays with the owner-side model — the question is now settled by data rather than doctrine.

## The false-positive program — ran and closed (2026-07-03): two levers shipped, the goal falsified

Pre-registered from a three-lineage research diff, run cumulatively on battery v3 (TRIAL.md): the **quote gate** and the **drop-biased cross-seat verifier** cut invented findings **5.6× at zero panel recall cost** and ship in v4.15; self-consistency voting (not significant) and k≥2 intersection (recall-destructive) failed their gates and do not. The **≤0.5-invented-per-review goal was falsified by its own stop rule**: the residual class — quotes that are real but don't entail the defect — measures 1.6 per clean panel review (LCB 0.80), and no verified technique removes it under the stdlib constraint. Negative shipped, per the harness precedent.

**Open, unblocking nothing:** the entailment successor (deterministic-ish claim-support checking; the sealed battery-v3 certification set — never opened — waits for it) · whole-repo-scale measurement.
