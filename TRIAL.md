# The Trial — measured results (battery trial-v1, 2026-07-02)

The skill's two central claims were, until now, *reasoned* rather than *measured* (see [ROADMAP.md](ROADMAP.md), which stated the success criteria before this ran). This is the first measurement. Raw responses are committed under `trials/results/` — re-score them yourself: `python3 trial_runner.py --report`.

**Setup.** 12 artifacts (code / prose / spec), 18 planted flaws, 3 clean decoys. Decorrelated authorship: codex and gemma each authored 3 defective artifacts and are never scored on their own (an author knows its answer key). Two seats — `gemma4:12b-mlx` (local, Gemini lineage) and `codex-default` (subscription, GPT lineage) — each ran three conditions per artifact: **lone** (a strict flaw-hunting persona), **protocol** (this skill's seat contract), **quick** (the Quick preset). **Panel** = the union of the protocol condition across seats, exactly what `--panel` hands the reducer. Grading is deterministic (anchor + fault-word windows; no LLM judges an LLM).

## Scoreboard

| condition | seat | recall | findings | invented (3 decoys) |
|---|---|---|---|---|
| lone | codex | 11/12 | 56 | **29** (~10 per clean artifact) |
| **protocol** | **codex** | **12/12** | **26** | **11** |
| quick | codex | 12/12 | 3† | 5 |
| lone | gemma | 12/12 | 4† | 0† |
| protocol | gemma | 10/12 | 8† | 0† |
| quick | gemma | 11/12 | 22 | 9 |
| **panel (union)** | both | **18/18** | — | 11 across 6 decoy-reviews |

† **Measurement limitation, stated plainly:** total findings are counted by the `[severity …]` markers the contracts request. Codex follows the format; gemma frequently names issues in prose without markers, so gemma's findings/invented cells (and any precision derived from them) are **undercounts** — several show fewer counted findings than flaws it demonstrably named. Gemma's *recall* is unaffected (recall grading is format-independent). Battery v2 owes a format-robust findings counter.

## What the numbers support

1. **The protocol beats the lone critic — on the same seat, same artifacts (the clean comparison, codex):** recall went *up* (11→12 of 12) while total findings *halved* (56→26) and invented problems on clean work dropped **2.6×** (29→11). The lone flaw-hunter fabricated ~10 problems per *defect-free* artifact; the protocol contract cut that to ~3.7 while missing nothing. This is the Reviewer-2 thesis, measured.
2. **The panel meets its pre-stated criterion:** union recall 18/18 — every planted flaw named by at least one seat, including the two gemma-protocol misses (covered by codex) and everything on each seat's blind spots — with an invented-problem load no worse than the best single seat's. Two caveats keep this honest: part of the union's advantage is *coverage* (each seat skips its own authored artifacts — in real use no seat authored your work), and gemma's invented-count is undermeasured (†).
3. **The Quick preset is the budget surprise:** near-perfect recall at a fraction of the finding volume — consistent with its design as the smallest useful unit.

## What they do not support

- No claim about artifact **scale** (fixtures are ≤200 words; the floor-probe's known artifact-scale gap stands).
- No cross-battery comparability: these numbers are **battery trial-v1** and n=1 per cell; treat them as a first measurement, not a benchmark.
- **Contamination clock:** the fixtures are now public; future model generations may train on them. Comparisons against future seats require a fresh battery (the harness makes that cheap).
