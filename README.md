# Spatiotemporal Critique

[![Release](https://img.shields.io/github/v/release/matteolopreti/spatiotemporal-critique)](https://github.com/matteolopreti/spatiotemporal-critique/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Claude skill](https://img.shields.io/badge/Claude-skill-d97757)](SKILL.md)
[![External critic: Ollama or cloud](https://img.shields.io/badge/external%20critic-Ollama%20%7C%20cloud-555)](EXTERNAL_CRITIC.md)

A review protocol that replaces the lone "critic persona." The lone critic only hunts for flaws, misses what you actually wanted, and breaks things that were already fine. This fixes that. It runs a **balanced, intent-anchored** review in two modes — *awake* (converge) and *asleep* (diverge) — sizes itself to the task, doing nothing for trivial work, and can pull in a **genuinely external viewpoint** (a different model, on demand) for real independence.

The lone critic fails in several overlapping ways; the framework answers them **many-to-many** — one failure can need several stages, and one stage can answer several failures:

- Manufactures problems, breaks good parts (Reviewer-2 bias) → **the four mandates**
- Wrong target — *mis-set*, *drifted*, or *stale* → **Origin** + the **Temporal anchor** (catches drift) + the **second-order net-improvement gate** (re-tests a stale rubric)
- Blind spots in the artifact as it stands → **the Spatial axis**
- Errors that live in the *history* of edits, not the draft → **the Temporal axis** (backward bisection — same axis, a different job)
- Saturation, overfitting to its own critics → **the Sleep regime**

---

## Five-minute start

- **Trivial, reversible edit?** Skip everything — the protocol declines itself.
- **Shipping real work (code, writing, a design, a plan)?** Paste the six [Quick-preset](SKILL.md#quick-preset-paste) questions and stop.
- **Want a second opinion that isn't just you again?** Turn on the [external reviewer](#optional-external-reviewer-real-independence) — a different-lineage model joins the panel.

**What it changes — one example.** *"Review my retry helper before I merge."*
- *Lone critic:* "No jitter, magic number `5`, use exponential backoff — rewrote it for you." Invents a requirement, rewrites working code, never asks the goal.
- *Spatiotemporal:* keeps the capped-retry + logging that handle the real failure mode; steelmans the fixed `5` for a fail-fast CLI; asks "bounded latency, not max reliability — confirm?"; flags the one real bug (unbounded sleep on the final attempt); verdict — one fix, ship the rest.

---

## At a glance

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

*Read top to bottom. Every step above is explained in full below* — the [four mandates](#four-mandates-always-on), [Configure to the task](#configure-to-the-task-run-first) (with the floor gate), the Awake stages (**Origin · Spatial · Temporal**), the Sleep stages (**Consolidate · Perturb**) and the [loop structure](#loop-structure), and [Scale](#scale-threads-through-everything). The optional [external reviewer](#optional-external-reviewer-real-independence) is the strongest rung of Spatial's independence ladder.

---

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

**Presets:** *Quick* (one paste, one context) · *Standard* (panel + one backward check) · *Full* (separate-call critics, full temporal, a sleep pass, external reviewer on). The paste prompts for **Quick** and **Standard** live in **[SKILL.md](SKILL.md)** (the operating procedure) — paste from there.

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

- **Map:** diverse critics run *independently* on the original, **each a single contribution** — its raw output is one viewpoint, not a balanced verdict, so balancing them is the panel's job, not the critic's. Independence has a quality ladder by **critic source**: same-context personas (degraded — they anchor on each other) < separate calls to the same model (better) < **a different model** — the **external reviewer**, run via `external_critic.py` (strongest — uncorrelated errors, an out-of-distribution check). Mix stance — domain-specific and generalist. Add a critic only when it buys a distinct failure surface: **coverage comes from diversity of stance, not headcount** (no fixed number).
- **Reduce — a separate, fresh-context synthesis pass.** Run synthesis in a *fresh context* that consumes the critiques as external inputs — not the context that produced them — so the synthesizer can't anchor on its own map (the one thing a "council" genuinely adds). Here the *synthesis-layer* mandates do their work (preserve-first, steelman): dedupe, rank by leverage (severity×confidence *and* blast radius), surface genuine disagreement as *contested* rather than auto-resolving, emit the preserve-list. With the external reviewer on, **cross-model agreement is strong corroboration and cross-model disagreement is a first-class contested point** — but the external critique is *input, not authority* (mandate 3 governs it).

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

## Optional: external reviewer (real independence)

One model in one session only *approximates* independence (same weights, correlated errors); for a genuinely uncorrelated view, route the artifact to a **different-lineage** model — local via [Ollama](https://ollama.com) or a cloud OpenAI-compatible endpoint — with the bundled `external_critic.py`, weighting it by *independence, not authority* (mandate 3 governs: reject it where it's wrong). It can also *surface* intent-level doubt for you to adjudicate, but cannot settle your goal. Full setup, model selection, the spec-aware picker, pin-and-log, and cloud routing live in **[EXTERNAL_CRITIC.md](EXTERNAL_CRITIC.md)**.

---

## Change log

**Self-gated.** From v4.0 on, every version bump must first pass this protocol run on its own spec (preserve-list · three highest-leverage issues · net-improvement gate). **Extension/refactor releases** must also be net lines-removed ≥ lines-added — the standing defense against bloat-on-extension. **Bugfix and explicitly-scoped feature releases are exempt from the line-count test** (a fix or a requested capability can't always shrink the tree), but must still justify every added line and consolidate any prose they touch.

- **v1** — four mandates + tiers + temporal passes. Backward pass caught a regression (fixing "too heavy" by adding scaffolding made it heavier).
- **v2** — added Origin and Sleep. The *same* regression recurred; consolidation named bloat-on-extension a **standing** property, making the prune pass permanent.
- **v3** — evaluated on five adversarial tasks; refactored the stakes-tiers into *configure-to-the-task* (tiers became presets); anchoring moved to best-corroborated-intent with an evolution/drift distinction.
- **v3.1** — made **scale** first-class (re-readings, not new machinery): outer-loop stop stated; perturbation given its near end; review cadence matched to blast-radius. Schematic + walkthrough added.
- **v3.2** — documented the **optional external reviewer** (Ollama) as the realization of the standing independence caveat: folded into Configure (opt-in dial) and Spatial (critic-source ladder; cross-model agreement/disagreement as synthesis signal), with `external_critic.py`, `setup.sh`, and guidance for safe auto-configuration. No core architecture change — stable.
- **v3.3** — model guidance brought current: default bumped off the older qwen2.5 generation to `qwen3:8b`, current candidates listed (Qwen3.x / GLM-4.7 / DeepSeek V3.2; a code-specialized tag for code), and the **config-first / ranked-list / pin-and-log-for-reproducibility** policy stated (auto-update can't be fully automated; pin+log keeps a review auditable). Documentation and defaults set here; the ranked-list / installed-first selection and per-run pin+log are now implemented in `setup.sh` / `external_critic.py` (config-first, with `.env` carrying setup's pick to the helper).
- **v3.4** — the external reviewer can now route to a **hosted OpenAI-compatible endpoint** (`CRITIC_BASE_URL` + `CRITIC_API_KEY`; default stays local Ollama, fully env-driven so it never persists off-machine routing), and `setup.sh` gained **spec-aware selection**: it reads RAM and auto-picks the strongest model that *safely* fits (skipping ones that would spill to CPU). A local benchmark (planted-bug code review) set the recommended default for a ~24 GB machine to **`gpt-oss:20b`** (4/5 bugs, fully GPU-resident, no hallucinations); cloud (e.g. GLM-5.2) stays the escalation for the subtlest cases. Stdlib-only and config-first preserved; no core architecture change.
- **v4.0** — first **self-gated** release (the protocol reviewed its own upgrade). Honesty + de-bloat + adoption pass: replaced the one-to-one failures↔fixes bijection with an honest **many-to-many lattice**; clarified that any reviewer — the external critic included — may *surface* intent-level doubt for the user to adjudicate, never a unilateral override or silent confirm; named the **fresh-context synthesis** pass and the external-reviewer seat; clarified that the four mandates bind at the **synthesis/reviser layers** (each critic is one source's view); split the external-reviewer setup into **EXTERNAL_CRITIC.md** and cut the ASCII schematic; added a five-minute start, a searchable heading, a dials decision-table and a **Standard preset**. Net lines removed ≥ added. *Deferred to v4.1: a confidence-term audit and an explicit abstention channel for critics.*
- **v4.1** — external-critic hardening (self-gated; the first **bugfix/feature** release). Fixed a **cloud-path bug**: the OpenAI-compatible route sent `seed`, which strict shims (e.g. Gemini's) reject with a 400 — the cloud critic was unusable on those endpoints; it now sends only universally-supported fields and surfaces the endpoint's own error text. Added **`--depth brief|full`** (terse default unchanged; `full` adds a rationale per finding, mirroring Quick/Standard sizing), **safe key handling** (load the API key from an OS secret store, never an inline `export`), and a **cloud lineage map** (pick a critic by vendor family, not a rotting leaderboard). **Refined the self-gate** so the net-negative line test binds on extension/refactor releases but exempts bugfix/feature ones (a fix can't always shrink the tree). Stdlib-only and config-first preserved. *Still deferred: the confidence-term audit and explicit abstention channel.*
- **v4.2** — external-critic **capability detection** (self-gated; a scoped **feature** release). *Availability ≠ capability:* a reachable seat can still be a **null** one — it summarizes or regenerates the artifact instead of finding its flaw (*independence-theater*). Applies the framework's own **planted-defect** discipline to the critic seat itself: **`--probe`** feeds the seat a tiny artifact with one known contradiction and grades the *answer* (a `<think>…</think>` block is stripped) with a **deterministic, non-LLM** string check — a different substrate, so it may *exclude* a null seat — PASS / FAIL / UNAVAILABLE. Adds a **`critic_registry.tsv`** capability log (newest record per model wins; a PASS over ~30 days is flagged stale) and **`--select`**, a *free+capable → paid+capable (confirm the spend) → same-lineage-flagged "independence degraded"* ladder; a **faithful `--probe FILE --expect "…"`** rung plants a flaw in a slice of your real artifact for the scale/abstraction-induced nulling a tiny probe misses; and a non-blocking **advisory** on a normal run when the seat has no capability-PASS on record. A PASS certifies the **read**, never authority over the **goal** — that residual stays the owner's. Externally reviewed (Gemini caught three grader-brittleness flaws, all fixed). Stdlib-only and config-first preserved.
- **v4.2.1** — fix (self-gated; a **bugfix** release). The **faithful `--probe FILE --expect`** parse lower-cased *and* space-stripped its tokens while `grade_probe` matches a **space-preserved** answer, so a **multi-word** expected finding (e.g. `"race condition"`) silently never matched — false-failing a capable seat (the same false-fail class v4.2's external review caught, surviving in this one path). Now it lower-cases but **preserves spaces**, mirroring the grader. Single-word `--expect` and the floor probe are unaffected.
- **v4.5** — **multi-provider keys** (self-gated; a scoped **feature** release). The guided setup now holds *several keys at once*: store each under its own item (`critic-api-key-<provider>`) and add ONE parameterized **`critic-env <provider>`** (a `case`/`switch` over the provider→base-URL map) that loads the right key per provider. So OpenAI + Google (etc.) **coexist** — `critic-env openai` → `--probe` a model, `critic-env google` → `--probe` a model, and `--select` builds **one panel spanning all your distinct lineages** (both keys recognized). The registry/panel were always multi-lineage; v4.5 makes the *key setup* multi-provider instead of a single shared item. Verified in a real shell: the generated `critic-env` flips base URLs per provider and errors on an unknown one. Stdlib-only and config-first preserved.
- **v4.4** — vendor-neutral setup + **model discovery** (self-gated; a scoped **feature** release). Stop hard-coding a model or a vendor. New **`critic_setup.py`** — cross-platform (macOS / Linux / Windows; zsh / bash / fish / PowerShell) **guided** setup: it detects your OS, shell, and RAM and prints a tailored, copy-pasteable path — the best local Ollama model for your RAM, *or* safe OS-secret-store key storage + a `critic-env` snippet for *your* shell. Detection + guidance only: it stores nothing, installs nothing, and pulls nothing on its own. New **`--discover`** lists the models a given key can serve (OpenAI-compat `/models`, or local Ollama), drops non-chat ids, **sorts newest-first** so a new release auto-surfaces, and annotates each with **free|paid tier + capability score** — you pick by score (no invented prices; no model API exposes them). Docs decoupled from any one vendor: a generic `critic-api-key` item, a `<provider-base-url>` placeholder, and Ollama-local/cloud · OpenAI · Google · DeepSeek · GLM · Mistral listed as equals. Externally reviewed (Gemini caught a non-native Windows credential cmdlet, a Windows key-history risk, two over-broad discovery filters, and a version-sort gap for unversioned ids — all fixed). Stdlib-only and config-first preserved.
- **v4.3** — capability **score + panel** (self-gated; a scoped **feature** release). The floor `--probe` is now **quantitative**: a two-flaw artifact (a contradiction + an impossible number) returns a **capability SCORE = how many flaws the seat NAMES** (0–N), so seats can be *ranked*, not just gated (PASS = score ≥ 1). The grader moved from per-flaw wordlists — which false-missed capable seats whose diagnosis vocabulary was open-ended ("negative memory footprint", "unrealistic") — to **subject-anchor + fault-word co-occurrence within a sentence or an adjacent pair**: tolerant of how a critique is phrased, yet a restating summary scores 0. `--select` becomes a **PANEL** of up to **3 capable seats across DISTINCT lineages** (independence = diversity; best-scoring per lineage, free-first), with paid seats flagged *"confirm the spend"* and never auto-used. Externally reviewed (Gemini caught an adjacent-sentence false-fail and a generic-word false-pass; both fixed). Stdlib-only and config-first preserved.
