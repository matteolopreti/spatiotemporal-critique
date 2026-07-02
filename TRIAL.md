# The Trial — measured results (battery trial-v1, 2026-07-02)

The skill's two central claims were, until now, *reasoned* rather than *measured* (see [ROADMAP.md](ROADMAP.md), which stated the success criteria before this ran). This is the first measurement. Raw responses are committed under `trials/results/` — re-score them yourself: `python3 trial_runner.py --report`.

**Setup.** 12 artifacts (code / prose / spec): **9 defective, each carrying exactly 2 planted flaws (= 18), plus 3 clean decoys carrying none**. Decorrelated authorship: codex and gemma each authored 3 defective artifacts and are never scored on their own (an author knows its answer key). Two seats — `gemma4:12b-mlx` (local, Gemini lineage) and `codex-default` (subscription, GPT lineage) — ran four conditions per artifact: **lone** (a strict flaw-hunting persona), **protocol** (this skill's seat contract), **quick** (the Quick preset), **standard** (the Standard preset shipped whole — the pre-registered v5.0 "protocol-as-brief" probe). **Panel** = the union of the protocol condition across seats, exactly what `--panel` hands the reducer. Grading is deterministic (anchor + fault-word windows; no LLM judges an LLM), and *invented* is deterministic **by construction**: a decoy contains zero planted defects, so every finding a condition emits on one is counted as invented.

## Scoreboard

| condition | seat | recall | findings | invented (3 decoys) |
|---|---|---|---|---|
| lone | codex | 11/12 | 56 | **29** (~10 per clean artifact) |
| **protocol** | **codex** | **12/12** | **26** | **11** |
| **standard** | **codex** | **12/12** | —† | **8** |
| quick | codex | 12/12 | 3† | 5† |
| lone | gemma | 12/12 | 4† | 0† |
| protocol | gemma | 10/12 | 8† | 0† |
| standard | gemma | 10/12 | 13 | 2† |
| quick | gemma | 11/12 | 22 | 9 |
| **panel (union)** | both | **18/18** | — | 11 across 6 decoy-reviews |

† **Measurement limitation, stated plainly:** total findings are counted by the `[severity …]` markers the contracts request. Codex follows the format; gemma frequently names issues in prose without markers, so gemma's findings/invented cells (and any precision derived from them) are **undercounts** — several show fewer counted findings than flaws it demonstrably named. Gemma's *recall* is unaffected (recall grading is format-independent). Battery v2 owes a format-robust findings counter.

## What the numbers support

1. **The protocol beats the lone critic — on the same seat, same artifacts (the clean comparison, codex):** recall went *up* (11→12 of 12) while total findings *halved* (56→26) and invented problems on clean work dropped **2.6×** (29→11). The lone flaw-hunter fabricated ~10 problems per *defect-free* artifact; the protocol contract cut that to ~3.7 while missing nothing. This is the Reviewer-2 thesis, measured.
2. **A dose-response curve on contract strength (the v5.0 probe):** on the measurable seat, invented problems fall monotonically as the contract gets fuller — lone **29** → protocol **11** → Standard-as-brief **8** — at unchanged 12/12 recall. Recall is **ceilinged by this battery** (nothing can exceed 12), so recall cannot discriminate the stronger contracts; only a harder battery can.
3. **The panel meets its pre-stated criterion, stated precisely:** union recall 18/18 — every planted flaw named by at least one seat, including the two gemma-protocol misses (covered by codex) — and the panel's *counted* invented load (11) matched codex-protocol's in absolute terms. Gemma's invented counts are not reliable enough (†) to support a "best single seat" comparison, so the criterion rests on the codex baseline. Second caveat: part of the union's recall advantage is *coverage* (each seat skips its own authored artifacts; in real use no seat authored your work).
4. **The Quick preset held recall at low volume — read with the counting caveat:** codex-quick shows only 3 counted findings (†, format markers) against 12/12 recall, so "low volume" is partly a counting artifact; gemma-quick (22 findings, format-compliant here) supports the same direction less dramatically. Treat this as *consistent with* the smallest-useful-unit design, not as a measured superiority claim.

## Reproducibility

Run at git ref `6a80a4d` (v4.12), 2026-07-02. Command: `python3 trial_runner.py` (calls the seats and scores) or `python3 trial_runner.py --report` (re-scores the committed raw responses only, no model calls). Fixtures: `trials/t01…t12` with the answer key in `trials/manifest.json` (per-flaw subject anchors + diagnosis vocabulary); raw responses: `trials/results/<seat>__<artifact>__<condition>.txt` (54 + 18 files). A flaw is **named** when some sentence — or adjacent sentence pair — in the critique contains one of its anchors *and* a fault word (the flaw's own `crit` list plus the probe's `PROBE_CRITICAL`); a **finding** is a `[severity …]` marker; an **invented problem** is any finding on a decoy. Example scoring window, verified on the committed bytes — artifact `t06`, flaw "impossible 143% latency reduction", reviewer gemma (t06 is codex-authored, so codex never reviews it): `trials/results/gemma__t06_prose__protocol.txt` line 8 reads `"reduced query latency by 143%" — A reduction of over 100% is mathematically impossible…` — the window contains anchor `143` and fault word `impossible` → named.

## What they do not support

- No claim about artifact **scale** (fixtures are ≤200 words; the floor-probe's known artifact-scale gap stands).
- No cross-battery comparability: these numbers are **battery trial-v1** and n=1 per cell; treat them as a first measurement, not a benchmark.
- **Contamination clock:** the fixtures are now public; future model generations may train on them. Comparisons against future seats require a fresh battery (the harness makes that cheap).
