# Roadmap

The framework is mature (v4.x); everything here is gated by the project's own rules — net-improvement, prune law, and **nothing graduates from a reasoned claim to a hard guarantee before its trial**.

## Shipped in v4.12

- ✅ **Plugin-marketplace packaging** — `/plugin marketplace add matteolopreti/spatiotemporal-critique`.
- ✅ **Docs split** — README (landing) · PROTOCOL.md (spec) · CHANGELOG.md (history).

## The Trial — ✅ run (2026-07-02): results in [TRIAL.md](TRIAL.md)

First measurement is in: the protocol beat the lone critic on the same seat (recall up, invented problems down 2.6×), and the panel union hit 18/18 recall within its pre-stated invented-problem bound. Caveats and the format-robust counter owed by battery v2 are in TRIAL.md. The original design, kept for reference:

## The Trial — measuring what is currently only reasoned

The skill's central claims — *the protocol beats a lone critic* and *a lineage-diverse panel beats a single seat* — are design arguments, not measurements (n = 1). The trial converts them, using the machinery the repo already has:

**Fixture set.** 12–16 small artifacts across the real use surface (code with planted bugs, prose with planted contradictions, specs with planted drift) **plus clean decoys containing no defect at all** — the decoys are non-negotiable, because the protocol's core promise is *fewer invented problems*, which only a false-positive measure can test.

**Decorrelated authorship.** Half the defects planted by a non-Claude lineage (codex/gemma), half by Claude; each seat is scored only on artifacts its own lineage did not author. (Lesson from prior work: a fixture whose author also wrote the answer key is a worked example, not a blind test.)

**Grading.** The existing deterministic anchor + fault-word grader (`score_probe`), generalized to a per-artifact manifest — no LLM judges an LLM.

**Conditions.** (1) lone-critic prompt (baseline) · (2) single probed seat under the protocol contract · (3) Quick preset · (4) panel union (up to 3 lineages).

**Metrics.** Recall (planted defects named) · precision (findings that map to real defects) · invented-problem rate on the clean decoys · abstention honesty.

**Falsifiable success criteria, stated before running:** the panel earns its cost only if it beats the best single seat on recall **without** a worse invented-problem rate. If it adds recall only by adding noise, the multi-seat claim fails and the docs get corrected accordingly. Estimated effort: ~1 day.

## v5.0 — gated on the Trial

- **Multi-council review** (up to 3 vendors, blind, union-of-findings, disagreement-first, Full tier only) is *already shipped* as `--panel`; v5.0 would extend it to a full **protocol-as-harness**: a different-lineage model running the whole spatiotemporal protocol (not just a critique seat), with a third lineage as its external check. Runs only if the Trial shows panel-grade value, and only on a budget that supports it (subscription seats first).
- Standing rules carried into any v5.0: agreement — even unanimous — is corroboration, never proof; model judgment raises, only deterministic checks gate; no combined verdicts, no green lights; intent adjudication stays human.
