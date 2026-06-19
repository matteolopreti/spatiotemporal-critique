# Spatiotemporal Critique — v3.4

A review protocol that replaces the lone "critic persona." The lone critic only hunts for flaws, misses what you actually wanted, and breaks things that were already fine. This fixes that. It runs a **balanced, intent-anchored** review in two modes — *awake* (converge) and *asleep* (diverge) — sizes itself to the task, doing nothing for trivial work, and can pull in a **genuinely external viewpoint** (a different model, on demand) for real independence.

The lone critic fails five ways; each has one dedicated fix, and that mapping is the framework:

- Manufactures problems, breaks good parts (Reviewer-2 bias) → **the four mandates**
- Optimizes toward a target that's wrong → **the Origin layer**
- Blind spots in the artifact as it stands → **the Spatial axis**
- Errors that live in the *history* of edits, not the draft → **the Temporal axis**
- Saturation, and overfitting to its own critics → **the Sleep regime**

---

## Schematic

```
  ALWAYS ON · preserve · steelman · discern · improvement-gate
  ───────────────────────────────────────────────────────────

                       TASK
                        │
                  ┌─────┴─────┐
                  │ Worth it? │ ─▶ trivial → just do it (skip it all)
                  └─────┬─────┘
                        │
             ╭──────────┴──────────╮
             │  CONFIGURE the task  │
             │  intent   given│ambig│
             │  verifier   yes│no   │
             │  ontology  corr│taste│
             │  control  human│auto │
             │  external   off│on   │ ◀ optional (Ollama)
             ╰──────────┬──────────╯
                        │
   ┌──────────── AWAKE · converge ────────────┐
   │                                          │
   │  ① ORIGIN — get the target right         │
   │     externalize intent · severe tests    │
   │     (not confirmation) · ledger          │
   │                    │                     │
   │  ② SPATIAL — coverage now                │
   │     independent critics ─▶ synthesis     │
   │     + preserve-list  (no lone nitpicker) │
   │     + optional EXTERNAL model            │ ◀ real independence
   │                    │                     │
   │  ③ TEMPORAL — trajectory integrity       │
   │     backward: which edit broke it        │
   │     forward: pre-mortem (hypotheses)     │
   │     anchor on best-corroborated intent   │
   │     (evolution ok · drift caught)        │
   │                                          │
   │     ↻ repeat until no material gain      │
   └─────────────────────┬────────────────────┘
                at the peak│
   ┌──────────── ASLEEP · diverge ────────────┐
   │                                          │
   │  ④ CONSOLIDATE                           │
   │     prune to the core · extract gist ·   │
   │     carry lessons across tasks           │
   │                    │                     │
   │  ⑤ PERTURB                               │
   │     near ▸ best nearby variant           │
   │     far  ▸ invert · cross-domain         │
   │     (find brittleness · recover missed)  │
   └─────────────────────┬────────────────────┘
                         │
      ↻ wake ⇄ sleep until STABLE under both
        (nothing changes & nothing better)
                         ▼
                    BETTER WORK

  SCALE threads through:  small → local·often·cheap
  big (direction) → global·rare·deep   [blast-radius ≈ time]
```

## How it works (plain walkthrough)

Read top to bottom. The four mandates sit above everything, always on. The first decision is whether to engage at all — trivial, easily-reversible work gets no framework. For everything else you read the task's shape on the dials, which set how much of each stage runs. Then the **awake** loop: fix the *target* first, look from several independent angles (optionally including a genuinely external model), then check the *trajectory* — which edit broke what, what might fail later, whether you've drifted — and repeat until a pass yields nothing material. At that peak you switch to **asleep**: prune to the core and extract the lesson, then perturb — nearby variants first, then aggressive cross-domain shake-up — to test for brittleness and recover anything cut too early. The whole wake⇄sleep cycle repeats until the work is stable under *both*. Two things run through all of it: **scale** (small decisions get cheap, frequent, local attention; direction gets rare, deep review — because how far a decision reaches is the same as how long it governs) and **intent** (the target is continuously re-checked, so you never perfect your aim at the wrong mark).

---

## Four mandates (always on)

1. **Preserve-first.** List what's working and must survive the edit *before* listing defects.
2. **Steelman before strike.** Argue why each current choice might already be right; if it survives, drop the critique.
3. **Discerning solver.** The reviser may reject a critique it judges wrong — blind compliance is how good parts break. *(This governs the external critic too.)*
4. **Net-improvement gate, two orders.** Keep a revision only if it beats the prior version on the rubric — *and* periodically re-test whether the rubric is still the right target. Allowed to exit with "leave it alone."

---

## Configure to the task (run first)

**Floor gate.** Trivial, low-stakes, easily-reversible work gets *no* framework — just do it. The framework must be willing to decline itself.

**Dials** (a few orienting questions, not a rigid taxonomy):

- **Intent — given or ambiguous?** Formal spec → Origin runs near-empty. Ambiguous → run Origin fully.
- **Verifier — present or absent?** Objective check exists → the temporal/executable axis dominates, critique is cheap. Absent → critique and corroboration carry the load.
- **Ontology — correctness or taste?** Correctness → the "issues / severity" vocabulary applies. Taste → report *what works and where it's generic*, not "defects."
- **Supervision — human or autonomous?** Human → Origin's severe tests go to the user. Autonomous → corroborate against held-out examples; escalate only high-blast-radius divergences.
- **External reviewer — off or on?** *(optional; see below)* On → a different model via Ollama joins the Spatial panel as a genuinely independent critic. Sensible at the Full tier or for code review; not for trivial tasks.

**Presets:** *Quick* (one paste, one context) · *Standard* (panel + one backward check) · *Full* (separate-call critics, full temporal, a sleep pass, external reviewer on).

### Quick preset (paste)

> Before I finalize this, run a balanced review:
> 1. What's working here that must be preserved?
> 2. Steelman my current choices — where might they already be right?
> 3. State what you think I'm actually trying to achieve, as a specific consequential claim I can confirm or correct. *(Skip if my goal is already formal.)*
> 4. List the assumptions you're making where I left things unspecified, and what breaks if each is wrong.
> 5. The 3 highest-leverage issues only, each with a concrete fix. *(Taste work: the 3 places it reads as generic, with a sharper alternative each.)*
> 6. Verdict: is this genuinely better than leaving it as is? If not, say so.

---

## Awake regime — converge

### ① Origin — get the target right (scales with the intent dial)

A perfectly critiqued, regression-free artifact built toward a misread intent is the worst output possible: confidently, coherently wrong, every check passed.

- **Externalize intent** as an inspectable, falsifiable spec the user can correct — not a latent "understanding" held by a persona, which only relocates the interpretation gap.
- **Severe tests, not confirmation.** Test with things that fail loudly when wrong: a *consequential* restatement that forces a boundary choice; a wrong-but-plausible alternative reading; and, when intent is set before generation, a *small concrete sample*.
- **Assumptions ledger, not a confidence score.** List every point where the spec was silent and you chose anyway, each with the consequence if wrong.
- **Triage by blast-radius.** Corroborate expensive-to-reverse decisions *before* building on them. When autonomous, this is the escalation filter.
- **Doubt the spec, not just your reading of it.** When literal compliance would betray the deeper goal, surface the divergence — never silently obey *or* silently override.

### ② Spatial — coverage at an instant (map-reduce)

- **Map:** diverse critics run *independently* on the original. Independence has a quality ladder by **critic source**: same-context personas (degraded — they anchor on each other) < separate calls to the same model (better) < **a different model** (strongest — uncorrelated errors, an out-of-distribution check). Mix stance — domain-specific and generalist. Coverage comes from diversity of stance, not headcount.
- **Reduce:** dedupe, rank by leverage (severity×confidence *and* blast radius), surface genuine disagreement as *contested* rather than auto-resolving, emit the preserve-list. With the external reviewer on, **cross-model agreement is strong corroboration and cross-model disagreement is a first-class contested point** — but the external critique is *input, not authority* (mandate 3 governs it).

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

Run by one model in one session, the framework's "independent critics" only *approximate* independence — same weights, same context, correlated errors. The fix is a **genuinely external viewpoint**: a different-lineage model run locally via [Ollama](https://ollama.com), joining the Spatial panel on demand.

- **What it buys:** uncorrelated errors and an out-of-distribution check. Agreement with the primary model is strong corroboration; disagreement is a contested point to surface.
- **Independence, not authority.** A local open model is usually weaker. Weight agreement; treat lone external claims skeptically. Mandate 3 (discerning solver) governs — reject it where it's wrong.
- **Scope.** It strengthens the *perspective* and *overfitting* axes, **not** the *intent* axis — only the user knows their goal. It can generate alternative readings (severe tests) but cannot confirm meaning.
- **Where it runs.** Anywhere the helper can execute — a local Ollama on `localhost:11434`, or outbound HTTPS to a cloud endpoint (`CRITIC_BASE_URL`). It needs a tool-executing context (agentic/CLI), not a hosted chat with no shell.

Helper: `external_critic.py` (dependency-free; returns PRESERVE / ISSUES-or-GENERIC / VERDICT, already shaped to feed synthesis).

### Choosing the model

The model is **config-first** (`CRITIC_MODEL`); never hardcode it — the in-script default is only a fallback. Pick a lineage *different from your primary model* (that is what buys the independence), and check `ollama.com/library` for the current tag, since rankings shift monthly:

- **Default / broadly runnable:** `qwen3:8b` — the in-script *floor* (a fallback only); `setup.sh` auto-picks the strongest installed model that safely fits your RAM (see the changelog for the current benchmarked pick).
- **Stronger general:** `qwen3:14b` / `qwen3:32b`, or a current GLM or DeepSeek tag (verify on `ollama.com/library`).
- **Code review:** a Qwen3-Coder or DeepSeek-Coder tag.

"Auto-update to the newest best model" can't be fully automated — *best* is a human judgment that changes monthly, and there's no clean registry query for it. The achievable design is config-first + a small **ranked preference list** (best first) the setup tries in order — reusing the strongest model you already have, else pulling a light default — refreshed by hand. And for reproducible work (scientific or code), **pin and log** the critic model used for a given review rather than silently auto-bumping mid-run — auto-update to stay current; pin+log (model, seed, params) so a review is auditable and reproducible on the same build (tags are mutable — re-pin after a re-pull). This is the same logged-trace discipline the Temporal axis and the assumptions ledger already use: record which critic produced the critique.

### Setup & test

```bash
# one-time, guided setup (installs nothing unless you pass --install)
chmod +x setup.sh external_critic.py
./setup.sh

# run it on a real file
python3 external_critic.py path/to/draft.md --brief "focus here" --mode correctness

# for code review, point at a current code model of a different lineage
# (verify the tag on ollama.com/library — these move monthly):
CRITIC_MODEL=qwen3-coder ./setup.sh

# or route to a hosted model (the artifact leaves your machine):
export CRITIC_BASE_URL=https://api.z.ai/api/paas/v4 CRITIC_API_KEY=... CRITIC_MODEL=glm-5.2
python3 external_critic.py path/to/draft.md --mode correctness
```

`setup.sh` writes its pick to `.env` for the helper and asks before any pull; `external_critic.py` logs the model, seed and params used on every run (`critique.log`, next to the helper; `--no-log` to skip) so a review is auditable.

**Local or cloud.** By default the critic is a *local* Ollama model — private, free, no keys. `setup.sh` reads your RAM and reuses the strongest model that comfortably fits (it won't auto-pick one too big for your machine). If nothing local is strong enough, set `CRITIC_BASE_URL` to an OpenAI-compatible endpoint (base URL including the version path, e.g. `.../v1`) plus `CRITIC_API_KEY`, and the same helper routes there instead — the cost is that the artifact leaves your machine. Independence comes from a *different lineage*, not from locality; local is just the private default.

For a **published skill**, automate *detection and guidance*, not silent installation: when the user turns the reviewer on, run the preflight; if Ollama isn't ready, report the one command (`./setup.sh`) and the approximate download size, and leave installing/pulling to explicit consent. Never silently install software or pull multi-GB models on a user's machine.

---

## Change log

- **v1** — four mandates + tiers + temporal passes. Backward pass caught a regression (fixing "too heavy" by adding scaffolding made it heavier).
- **v2** — added Origin and Sleep. The *same* regression recurred; consolidation named bloat-on-extension a **standing** property, making the prune pass permanent.
- **v3** — evaluated on five adversarial tasks; refactored the stakes-tiers into *configure-to-the-task* (tiers became presets); anchoring moved to best-corroborated-intent with an evolution/drift distinction.
- **v3.1** — made **scale** first-class (re-readings, not new machinery): outer-loop stop stated; perturbation given its near end; review cadence matched to blast-radius. Schematic + walkthrough added.
- **v3.2** — documented the **optional external reviewer** (Ollama) as the realization of the standing independence caveat: folded into Configure (opt-in dial) and Spatial (critic-source ladder; cross-model agreement/disagreement as synthesis signal), with `external_critic.py`, `setup.sh`, and guidance for safe auto-configuration. No core architecture change — stable.
- **v3.3** — model guidance brought current: default bumped off the older qwen2.5 generation to `qwen3:8b`, current candidates listed (Qwen3.x / GLM-4.7 / DeepSeek V3.2; a code-specialized tag for code), and the **config-first / ranked-list / pin-and-log-for-reproducibility** policy stated (auto-update can't be fully automated; pin+log keeps a review auditable). Documentation and defaults set here; the ranked-list / installed-first selection and per-run pin+log are now implemented in `setup.sh` / `external_critic.py` (config-first, with `.env` carrying setup's pick to the helper).
- **v3.4** — the external reviewer can now route to a **hosted OpenAI-compatible endpoint** (`CRITIC_BASE_URL` + `CRITIC_API_KEY`; default stays local Ollama, fully env-driven so it never persists off-machine routing), and `setup.sh` gained **spec-aware selection**: it reads RAM and auto-picks the strongest model that *safely* fits (skipping ones that would spill to CPU). A local benchmark (planted-bug code review) set the recommended default for a ~24 GB machine to **`gpt-oss:20b`** (4/5 bugs, fully GPU-resident, no hallucinations); cloud (e.g. GLM-5.2) stays the escalation for the subtlest cases. Stdlib-only and config-first preserved; no core architecture change.
