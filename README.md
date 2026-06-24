# Spatiotemporal Critique

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

**Self-gated.** From v4.0 on, every version bump must first pass this protocol run on its own spec (preserve-list · three highest-leverage issues · net-improvement gate), and the diff must be net lines-removed ≥ lines-added — the standing defense against bloat-on-extension.

- **v1** — four mandates + tiers + temporal passes. Backward pass caught a regression (fixing "too heavy" by adding scaffolding made it heavier).
- **v2** — added Origin and Sleep. The *same* regression recurred; consolidation named bloat-on-extension a **standing** property, making the prune pass permanent.
- **v3** — evaluated on five adversarial tasks; refactored the stakes-tiers into *configure-to-the-task* (tiers became presets); anchoring moved to best-corroborated-intent with an evolution/drift distinction.
- **v3.1** — made **scale** first-class (re-readings, not new machinery): outer-loop stop stated; perturbation given its near end; review cadence matched to blast-radius. Schematic + walkthrough added.
- **v3.2** — documented the **optional external reviewer** (Ollama) as the realization of the standing independence caveat: folded into Configure (opt-in dial) and Spatial (critic-source ladder; cross-model agreement/disagreement as synthesis signal), with `external_critic.py`, `setup.sh`, and guidance for safe auto-configuration. No core architecture change — stable.
- **v3.3** — model guidance brought current: default bumped off the older qwen2.5 generation to `qwen3:8b`, current candidates listed (Qwen3.x / GLM-4.7 / DeepSeek V3.2; a code-specialized tag for code), and the **config-first / ranked-list / pin-and-log-for-reproducibility** policy stated (auto-update can't be fully automated; pin+log keeps a review auditable). Documentation and defaults set here; the ranked-list / installed-first selection and per-run pin+log are now implemented in `setup.sh` / `external_critic.py` (config-first, with `.env` carrying setup's pick to the helper).
- **v3.4** — the external reviewer can now route to a **hosted OpenAI-compatible endpoint** (`CRITIC_BASE_URL` + `CRITIC_API_KEY`; default stays local Ollama, fully env-driven so it never persists off-machine routing), and `setup.sh` gained **spec-aware selection**: it reads RAM and auto-picks the strongest model that *safely* fits (skipping ones that would spill to CPU). A local benchmark (planted-bug code review) set the recommended default for a ~24 GB machine to **`gpt-oss:20b`** (4/5 bugs, fully GPU-resident, no hallucinations); cloud (e.g. GLM-5.2) stays the escalation for the subtlest cases. Stdlib-only and config-first preserved; no core architecture change.
- **v4.0** — first **self-gated** release (the protocol reviewed its own upgrade). Honesty + de-bloat + adoption pass: replaced the one-to-one failures↔fixes bijection with an honest **many-to-many lattice**; clarified that any reviewer — the external critic included — may *surface* intent-level doubt for the user to adjudicate, never a unilateral override or silent confirm; named the **fresh-context synthesis** pass and the external-reviewer seat; clarified that the four mandates bind at the **synthesis/reviser layers** (each critic is one source's view); split the external-reviewer setup into **EXTERNAL_CRITIC.md** and cut the ASCII schematic; added a five-minute start, a searchable heading, a dials decision-table and a **Standard preset**. Net lines removed ≥ added. *Deferred to v4.1: a confidence-term audit and an explicit abstention channel for critics.*
