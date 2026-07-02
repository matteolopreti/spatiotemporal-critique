# The Trial — measured results (battery trial-v1, 2026-07-02)

The skill's two central claims were, until now, *reasoned* rather than *measured* (see [ROADMAP.md](ROADMAP.md), which stated the success criteria before this ran). This is the first measurement. Raw responses are committed under `trials/results/` — re-score them yourself: `python3 trial_runner.py --report`.

**Setup.** 12 artifacts (code / prose / spec): **9 defective, each carrying exactly 2 planted flaws (= 18), plus 3 clean decoys carrying none**. Decorrelated authorship: codex and gemma each authored 3 defective artifacts and are never scored on their own (an author knows its answer key). Two seats — `gemma4:12b-mlx` (local, Gemini lineage) and `codex-default` (subscription, GPT lineage) — ran four conditions per artifact: **lone** (a strict flaw-hunting persona), **protocol** (this skill's seat contract), **quick** (the Quick preset), **standard** (the Standard preset shipped whole — the pre-registered v5.0 "protocol-as-brief" probe). **Panel** = the union of the protocol condition across seats, exactly what `--panel` hands the reducer. Grading is deterministic (anchor + fault-word windows; no LLM judges an LLM), and *invented* is deterministic **by construction**: a decoy contains zero planted defects, so every finding a condition emits on one is counted as invented.

## Scoreboard

*(Scoreboard re-scored 2026-07-02 with the format-robust counter v2 — markers plus ISSUES-block list items. The counter upgrade **corrected one of this report's own earlier conclusions**; see finding 2. The superseded marker-only numbers are preserved in git history at ref `4489fb1`.)*

| condition | seat | recall | findings | invented (3 decoys) |
|---|---|---|---|---|
| lone | codex | 11/12 | 56 | **29** (~10 per clean artifact) |
| **protocol** | **codex** | **12/12** | **26** | **11** |
| standard | codex | 12/12 | 33 | 15 |
| quick | codex | 12/12 | 18 | 9 |
| lone | gemma | 12/12 | 4† | 0† |
| protocol | gemma | 10/12 | 13 | 5 |
| standard | gemma | 10/12 | 19 | 9 |
| quick | gemma | 11/12 | 22 | 9 |
| **panel (union)** | both | **18/18** | — | 16 across 6 decoy-reviews (2.67/review) |

† **Remaining measurement limitation, stated plainly:** counter v2 counts `[severity …]` markers, falling back to list items inside an ISSUES/GENERIC block. Gemma's **lone** responses use free-form prose with neither, so its lone-row findings/invented cells are still undercounts. All other cells are now measured. Recall grading is format-independent throughout.

## What the numbers support

1. **The protocol beats the lone critic — on the same seat, same artifacts (the clean comparison, codex):** recall went *up* (11→12 of 12) while total findings *halved* (56→26) and invented problems on clean work dropped **2.6×** (29→11). The lone flaw-hunter fabricated ~10 problems per *defect-free* artifact; the protocol contract cut that to ~3.7 while missing nothing. This is the Reviewer-2 thesis, measured.
2. **A published conclusion, corrected by a better ruler (the v5.0 probe):** the first scoring of the Standard-as-brief condition showed invented problems falling monotonically with contract strength (29 → 11 → 8) — **that was a counting artifact**; the marker-only counter missed standard-codex's unmarked findings. Re-scored with counter v2: **the plain protocol contract is the noise optimum (11); the fuller Standard brief made the same seat *noisier* on clean work (15) at identical 12/12 recall.** More protocol in one seat's prompt is not better — a result that argues *against* a protocol-as-harness, not for it. (Recall remains ceilinged by this battery: nothing can exceed 12, so recall cannot discriminate the stronger contracts.)
3. **The panel meets its pre-stated criterion on the rate basis, stated precisely:** union recall 18/18 — every planted flaw named by at least one seat, including the two gemma-protocol misses (covered by codex). Invented load: the union's summed total is **16** across 6 decoy-reviews (**2.67 per review**) versus codex-protocol's 11 across 3 (**3.67 per review**) — the *rate* criterion holds; the absolute wading volume is higher because two seats' noise adds. Caveat: part of the union's recall advantage is *coverage* (each seat skips its own authored artifacts; in real use no seat authored your work).
4. **The Quick preset is middling under honest counting:** 12/12 recall at 18 findings / 9 invented (codex) — between lone and protocol on noise, consistent with its smallest-useful-unit design; the earlier "budget surprise" framing rested on the undercount and is withdrawn.

## Reproducibility

Run at git ref `6a80a4d` (v4.12), 2026-07-02. Command: `python3 trial_runner.py` (calls the seats and scores) or `python3 trial_runner.py --report` (re-scores the committed raw responses only, no model calls). Fixtures: `trials/t01…t12` with the answer key in `trials/manifest.json` (per-flaw subject anchors + diagnosis vocabulary); raw responses: `trials/results/<seat>__<artifact>__<condition>.txt` (54 + 18 files). A flaw is **named** when some sentence — or adjacent sentence pair — in the critique contains one of its anchors *and* a fault word (the flaw's own `crit` list plus the probe's `PROBE_CRITICAL`); a **finding** is a `[severity …]` marker; an **invented problem** is any finding on a decoy. Example scoring window, verified on the committed bytes — artifact `t06`, flaw "impossible 143% latency reduction", reviewer gemma (t06 is codex-authored, so codex never reviews it): `trials/results/gemma__t06_prose__protocol.txt` line 8 reads `"reduced query latency by 143%" — A reduction of over 100% is mathematically impossible…` — the window contains anchor `143` and fault word `impossible` → named.

## Battery v2 — artifact scale, three vendors, the harness experiment (2026-07-02)

8 fixtures at real-document scale (300–1200 words / 70–110 code lines), **subtler flaws** (inverted expiry arithmetic, an SLO budget off by one nine, timeline-vs-causality contradictions, a far-apart circular dependency), 14 planted flaws + 2 clean decoys. Three authoring lineages (claude / codex / **gemini API** / gemma); every planted line verified present verbatim before the run; author answer keys committed (`trials/v2/*.key.txt`). Three seats × five conditions — including **harness**: the *entire* PROTOCOL.md as the seat's orchestrator brief, the protocol-as-harness proxy the v5.0 gate demanded.

| condition | codex (recall · invented) | gemini (recall · invented) | gemma (recall · invented) |
|---|---|---|---|
| lone | 10/10 · **29** | 9/9 · 9 | 10/12 · 3 |
| **protocol** | **10/10 · 11** | 8/9 · **5** | 10/12 · 5 |
| standard | 10/10 · 11 | 9/9 · 6 | 10/12 · 5 |
| harness | 10/10 · 12 | 9/9 · 7 | **9/12** · 6 |
| quick | 10/10 · 6 | 9/9 · 7 | 8/12 · 4 |
| **panel (protocol union)** | **14/14 · 21/6 reviews** | | |
| panel (harness union) | 14/14 · 25/6 reviews | | |

**What v2 establishes:**

1. **The core claim replicates — across batteries and across vendors.** Protocol vs lone on the two strong seats: codex 29→11 invented (2.6×, same factor as battery v1), gemini 9→5, at equal recall. On gemma (a 12B local model that was already low-noise) the noise gain is absent — the protocol's fabrication cut is a strong-seat effect, said plainly.
2. **The harness is falsified.** The full-protocol brief beat the plain seat contract *nowhere*: equal recall with more noise on codex (12 vs 11 invented, 37 vs 26 findings) and gemini (7 vs 5, 31 vs 13), and on the small local seat it *lost recall* (9/12 vs 10/12) — the heavier brief degraded it. The panel built from harness seats was strictly worse than the protocol panel (25 vs 21 invented at identical 14/14 recall). **Verdict: a protocol-as-harness adds volume, not detection — the v5.0 gate closes on its own pre-registered experiment.**
3. **The panel remains the recall mechanism:** 14/14 on flaws subtle enough that individual seats missed them, at a 3.5-invented-per-review rate.
4. **Top seats saturate even this battery** (codex 10/10 everywhere) — discriminating *between* strong seats on recall would need a battery v3; the harness question didn't need it, because the noise axis already discriminated.

## Battery v3 — the false-positive-suppression program (2026-07-03)

The follow-up program asked: can invented findings on clean artifacts be driven from ~3.5 per review toward **≤0.5**, paying at most one planted flaw of recall? Everything was pre-registered before any run (criteria, stop rules, statistics); levers ran **cumulatively**, each read as a paired delta on identical fixtures; grading stayed deterministic; raw responses are committed in `trials/v3/results/` and re-scorable with `--report`.

| cumulative stack | invented / clean seat-review | panel recall |
|---|---|---|
| shipped v4.13 contract (baseline) | 3.21 (45 over 14 reviews) | 14/14 |
| + **quote gate** (findings must QUOTE the work; deterministic substring check) | 1.43 — p = 0.0013 | 14/14 |
| + **cross-seat verification** (drop-biased, different lineage) | **0.57** — p = 0.018 | **14/14** |
| + self-consistency (2-of-3 samples) | 0.43 — p = 0.40, **not adopted** | 14/14 |
| + k≥2 panel intersection | 0.40/panel-review at recall **8/14** — **disqualified** | — |

**What v3 establishes:**

1. **The quote gate works mostly through behavior, not filtering.** Only 7 of the 25 removed findings died at the deterministic check — seats invent less when forced to quote. Zero panel recall cost. On the 12B local seat the gate traded 3 seat-level flaws for near-silence (panel union covered them) — the small-seat caveat, now measured.
2. **The verifier-polarity dispute settled by data.** A keep-biased verifier was a no-op (p = 0.5); the skeptical drop-biased verifier cut invented findings 60% at zero panel recall cost. Our own source-verified research brief predicted the opposite; the measurement won.
3. **A decoy was retired by its own reviewers.** All three lineages independently flagged an unbounded per-key counter dict in `v2t8_code.py`. By this battery's own standards (v2 *plants* resource leaks as flaws) the finding is real — the artifact left the clean set, and ~3 of the "invented" findings in the v2 table above carry this footnote.
4. **The ≤0.5 goal was falsified by its own pre-registered stop rule.** Every surviving false positive is one class — the quote is real but does not *entail* the defect (omission-demands on short specs, contract-boundary disputes) — measured at **1.6 per clean panel review (95% lower bound 0.80)**, 3× the goal. Nothing in the verified literature removes that class under these constraints. The certification set (10 sealed clean decoys + 4 planted artifacts) was never opened; it waits, virgin, for a successor program on entailment checking.

**v4.15 ships levers 1+2** as the default seat contract and the `--panel` verification pass (`--no-verify` opts out). Dropped findings are marked, never silently deleted.

## What they do not support

- No claim about full repo/project **scale** (battery v2 reaches ~1200-word documents; whole-codebase reviews remain unmeasured).
- No cross-battery comparability: these numbers are **battery trial-v1** and n=1 per cell; treat them as a first measurement, not a benchmark.
- **Contamination clock:** the fixtures are now public; future model generations may train on them. Comparisons against future seats require a fresh battery (the harness makes that cheap). The battery-v3 *certification* set is committed but was never shown to any seat — it stays valid until models train on this repo.
- **Battery v3 bounds:** single run per cell, fixture scale; the 5.6× is measured against this battery's baseline, not a universal constant; the entailment-failure classification is a single adjudicator's documented judgment, re-checkable from the committed survivors.
