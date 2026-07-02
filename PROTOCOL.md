# The Spatiotemporal Critique protocol — full specification

This is the canonical framework spec. The [README](README.md) is the landing page (what it is, install, FAQ); [SKILL.md](SKILL.md) is the operating procedure with the paste presets; this file is the *why and how* of every stage.

---

## The loop, schematically

```
  ALWAYS ON — the four mandates   (balance is the panel's job, not any one critic's)
      synthesis layer:  preserve-first · steelman
      reviser layer:    discerning-solver · improvement-gate

  task ─▶ trivial & reversible? ─▶ just do it   (the framework declines itself)
       ▼ else
  CONFIGURE ─▶ intent · verifier · ontology · supervision · external?
       ▼
  ── AWAKE · converge ───────────────────────────────
     ① Origin    → get the target right · externalize · severe tests ·
                   surface intent-doubt for the user to adjudicate
     ② Spatial   → independent critics ▶ fresh-context synthesis ▶ preserve-list
     ③ Temporal  → backward (what broke) · forward (what might fail) ·
                   re-anchor on the best-corroborated intent
        ↻ repeat until a pass finds nothing material
       ▼ at the peak
  ── ASLEEP · diverge ───────────────────────────────
     ④ Consolidate → prune to the core · extract the rule (gist)
     ⑤ Perturb     → near + far: find brittleness, recover options
        ↻ wake ⇄ sleep until stable under both

  ─▶ BETTER WORK      ·      scale threads through · blast-radius ≈ time-scale
```

## How it works (plain walkthrough)

Read top to bottom. The four mandates sit above everything, always on. The first decision is whether to engage at all — trivial, easily-reversible work gets no framework. For everything else you read the task's shape on the dials, which set how much of each stage runs. Then the **awake** loop: fix the *target* first, look from several independent angles (optionally including a genuinely external model), then check the *trajectory* — which edit broke what, what might fail later, whether you've drifted — and repeat until a pass yields nothing material. At that peak you switch to **asleep**: prune to the core and extract the lesson, then perturb — nearby variants first, then aggressive cross-domain shake-up — to test for brittleness and recover anything cut too early. The whole wake⇄sleep cycle repeats until the work is stable under *both*. Two things run through all of it: **scale** (small decisions get cheap, frequent, local attention; direction gets rare, deep review — because how far a decision reaches is the same as how long it governs) and **intent** (the target is continuously re-checked, so you never perfect your aim at the wrong mark).

---

## Four mandates (always on)

They bind at two layers — not inside each critic. Each critic is **one source's view**; even the external seat's preserve/issues/verdict is *raw input the synthesis re-balances*, never the authoritative review. **Balance is a property of the panel and its synthesis pass, not of any one critic.**

1. **Preserve-first** *(synthesis layer)*. List what's working and must survive the edit *before* listing defects.
2. **Steelman before strike** *(synthesis layer)*. Argue why each current choice might already be right; if it survives, drop the critique.
3. **Discerning solver** *(reviser layer)*. The reviser may reject a critique it judges wrong — blind compliance is how good parts break. *(This is how the reviser treats the external critic too.)*
4. **Net-improvement gate, two orders** *(reviser layer)*. Keep a revision only if it beats the prior version on the rubric — *and* periodically re-test whether the rubric is still the right target. Allowed to exit with "leave it alone."

---

## Configure to the task (run first)

**Floor gate.** Trivial, low-stakes, easily-reversible work gets *no* framework — just do it. The framework must be willing to decline itself.

**Dials** — read the task's shape; each setting sets how much of each stage runs:

| Dial | Setting → which stages run, at what depth |
| --- | --- |
| **Intent** | given → Origin near-skip · ambiguous → run Origin fully (externalize + severe tests) |
| **Verifier** | present → the Temporal/executable axis dominates, critique is cheap · absent → Spatial critique + corroboration carry it |
| **Ontology** | correctness → the issues × severity vocabulary · taste → "what works / where it reads generic", not "defects" |
| **Supervision** | human → Origin's severe tests go to the user · autonomous → corroborate vs held-out examples, escalate only high-blast-radius |
| **External** | off → in-session panel only · on → a different-lineage model joins the Spatial panel (Full preset / code review) |

**Presets:** *Quick* (one paste, one context) · *Standard* (panel + one backward check) · *Full*. The paste prompts for **Quick** and **Standard** live in **[SKILL.md](SKILL.md)** (the operating procedure) — paste from there. *Full* is not a paste: it is Standard **plus** the external panel (`--panel`), the full temporal pass over real history, and a sleep pass — the skill assembles it when the stakes warrant it.

---

## Awake regime — converge

### ① Origin — get the target right (scales with the intent dial)

A perfectly critiqued, regression-free artifact built toward a misread intent is the worst output possible: confidently, coherently wrong, every check passed.

- **Externalize intent** as an inspectable, falsifiable spec the user can correct — not a latent "understanding" held by a persona, which only relocates the interpretation gap.
- **Severe tests, not confirmation.** Test with things that fail loudly when wrong: a *consequential* restatement that forces a boundary choice; a wrong-but-plausible alternative reading; and, when intent is set before generation, a *small concrete sample*.
- **Assumptions ledger, not a confidence score.** List every point where the spec was silent and you chose anyway, each with the consequence if wrong.
- **Triage by blast-radius.** Corroborate expensive-to-reverse decisions *before* building on them. When autonomous, this is the escalation filter.
- **Doubt the spec, not just your reading of it.** When literal compliance would betray the deeper goal, *surface* the divergence for the user to adjudicate — never silently obey, silently override, *or* silently confirm. This surfacing duty is first-class and governs every critic, the external model included.

### ② Spatial — coverage at an instant (map-reduce)

- **Map:** diverse critics run *independently* on the original, **each a single contribution** — its raw output is one viewpoint, not a balanced verdict, so balancing them is the panel's job, not the critic's. Independence has a quality ladder by **critic source**: same-context personas (degraded — they anchor on each other) < separate calls to the same model (better) < **a different model** — the **external critic**, run via `external_critic.py` (strongest — uncorrelated errors, an out-of-distribution check). Mix stance — domain-specific and generalist. Add a critic only when it buys a distinct failure surface: **coverage comes from diversity of stance, not headcount** (no fixed number).
- **Reduce — a separate, fresh-context synthesis pass.** Run synthesis in a *fresh context* that consumes the critiques as external inputs — not the context that produced them — so the synthesizer can't anchor on its own map (the one thing a "council" genuinely adds). Here the *synthesis-layer* mandates do their work (preserve-first, steelman): dedupe, rank by leverage (severity×confidence *and* blast radius), surface genuine disagreement as *contested* rather than auto-resolving, emit the preserve-list. With the external reviewer on, **cross-lineage agreement is corroboration — never proof (vendors share training data) — and cross-model disagreement is a first-class contested point** — but the external critique is *input, not authority* (mandate 3 governs it).
- **Abstention is a first-class answer.** Any critic may return "ABSTAIN: *what* — *why*" instead of a finding it can't actually stand behind (missing context, outside competence, truncated input). Synthesis treats an abstention as a **coverage gap to report, never as agreement** — honest abstention is what separates a weak-but-genuine critic from a null one that fills the page.

**Confidence vocabulary (used throughout):** *corroborated* — independent sources agree; act on it. *contested* — independent sources disagree; surface it, the user weighs. *hypothesis* — single-source and untested; verify before building on it. "Confidence" in the leverage ranking means this corroboration level — never a self-reported percentage.

### ③ Temporal — trajectory integrity across time

- **Backward = bisection** over a *real logged trace* (every version, which agent changed what, and why). Localize any regression to the exact edit. With a verifier, the regression check is *executable* — run the tests.
- **Forward = pre-mortem.** Stipulate "this shipped and failed — explain why." Treat output as *low-confidence hypotheses* (the most hallucination-prone step). Its core question — which assumption, if wrong, invalidates the most downstream work — feeds the triage.
- **Bounded branching:** at a regression point, branch and try an alternative; keep the best leaf. Single meta-pass, fixed budget.
- **Anchor on the best-corroborated intent so far** — *not* the last draft (drift) and *not* the original goal by default (intent can legitimately evolve). The ledger records every intent change, so corroborated **evolution** stays legible and silent **drift** stays catchable.
- **Inner stop:** no material new issue, or a fixed cap.

---

## Sleep regime — diverge (offline)

Everything above is convergent and online: it narrows toward a well-defended local optimum — the recipe for the two pathologies it cannot self-correct: **saturation** and **overfitting to its own critics**. The sleep regime is the missing half.

"Offline" is implementable: run the pass with the local *optimize-this-draft* objective withheld and a structural objective substituted, so it cannot just re-optimize locally.

### ④ Consolidate — prune and generalize
- **Prune-and-renormalize.** Strip the artifact and its accreted scaffolding back to the load-bearing core — the standing defense against bloat.
- **Cross-trajectory consolidation** (*between* tasks). The error recurring across drafts, the revision pattern revealing an unstated preference — feed both to the origin layer. One task's ledger becomes the next's prior.
- **Gist.** Step up an abstraction level: what rule is this an instance of, and does seeing it change the artifact?

### ⑤ Perturb — against overfitting, at two scales
A divergent pass that is *not* trying to improve or find errors:
- **Near** — explore nearby variants (phrasing, ordering, a parameter ±10%) to find the best *neighbor*, **even when no critic flagged a defect**.
- **Far** — invert a core assumption, generate a deliberately strange variant, recombine across unrelated domains.

Together they **detect overfitting** (a polished artifact that shatters under mild perturbation was overfit) and **recover non-local alternatives** the gate pruned too early. *(An external model is itself a far-perturbation: it doesn't share Claude's priors, so it exposes Claude-overfit choices.)*

### Loop structure
**Alternation, not a fixed cycle count.** Renormalize, then perturb, then re-consolidate — the order is load-bearing; the number of rounds is not. The inner awake loop stops at the inverted-U's peak; that peak is where you *sleep*, then resume from cleaner signal. **Outer stop:** halt when a full wake⇄sleep cycle changes nothing *and* perturbation (near and far) finds nothing better.

---

## Scale (threads through everything)

Match the review to the decision's scale: small calls get **local, frequent, cheap** attention; direction-level calls get **global, rare, deep** review. **Blast-radius and time-scale are two readings of one axis** (a high-blast-radius decision governs a long stretch of downstream work), so the reversibility triage is also the scale control.

---

## The orchestrator contract — running the protocol from another model

The protocol is host-agnostic: any capable model may execute it (the *harness* condition in [TRIAL.md](TRIAL.md) does exactly that — the whole spec as one seat's brief). A non-Claude orchestrator must honor, without exception:

1. **The four mandates, at their layers** — preserve-first and steelman in its synthesis; discerning-solver and the net-improvement gate in its revisions.
2. **Abstention over fabrication.** Where it cannot genuinely judge, it says `ABSTAIN: what — why`; an honest gap beats a filled page.
3. **No green lights.** Its output is findings plus a verdict that never *certifies* — a reviewer can only raise problems or fail to raise them. Clearance, and the intent itself, stay with the human owner.
4. **Agreement discipline.** Cross-lineage agreement is corroboration, never proof; same-lineage agreement is near-uninformative; findings are reported as a union, disagreement first.
5. **Temporal honesty.** Backward bisection runs on a real trace (git by default) or is skipped and said so — never an invented history.
6. **Synthesis ownership.** Unless the owner explicitly transfers the reducer role, synthesis stays with the owner-side model; an external orchestrator's own synthesis arrives as *one more input* to that reducer, not as the review.
7. **The trust plumbing, when it drives the tools.** Seats it recruits must be probe-certified; paid calls stay spend-gated; runs stay pin-logged.

*Standing empirical note:* the first harness measurements (TRIAL.md) found that giving one seat a fuller protocol brief did **not** improve it — the plain seat contract was the noise optimum. Any orchestrator deployment must re-run that comparison on the current battery before claiming to add value.
