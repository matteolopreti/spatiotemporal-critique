# Spatiotemporal Critique

[![Release](https://img.shields.io/github/v/release/matteolopreti/spatiotemporal-critique)](https://github.com/matteolopreti/spatiotemporal-critique/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Claude skill](https://img.shields.io/badge/Claude-skill-d97757)](SKILL.md)
[![External critic: Ollama or cloud](https://img.shields.io/badge/external%20critic-Ollama%20%7C%20cloud-555)](EXTERNAL_CRITIC.md)

A review protocol that replaces the lone "critic persona." A lone critic only hunts for flaws: it invents problems, misses what you actually wanted, and breaks things that were already fine. This protocol runs a **balanced, intent-anchored** review instead — in two modes, *awake* (converge) and *asleep* (diverge) — sizes itself to the task (trivial work gets no ceremony), and can add a **genuinely external viewpoint**: a different model family, local or cloud, so the second opinion isn't just you again.

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
- **Want a second opinion that isn't just you again?** [Install](#install) the external critic — a different-lineage model joins the panel.

**What it changes — one example.** *"Review my retry helper before I merge."*
- *Lone critic:* "No jitter, magic number `5`, use exponential backoff — rewrote it for you." Invents a requirement, rewrites working code, never asks the goal.
- *Spatiotemporal:* keeps the capped-retry + logging that handle the real failure mode; steelmans the fixed `5` for a fail-fast CLI; asks "bounded latency, not max reliability — confirm?"; flags the one real bug (unbounded sleep on the final attempt); verdict — one fix, ship the rest.

---

## Install

The protocol itself is a *procedure* — nothing to install; paste the presets from [SKILL.md](SKILL.md). The optional **external critic** is a small stdlib-only Python helper:

```bash
git clone https://github.com/matteolopreti/spatiotemporal-critique
cd spatiotemporal-critique

# 1 · a local reviewer — free, private (needs https://ollama.com installed):
./setup.sh                                # picks a model that fits your RAM; asks before pulling

# 2 · certify the seat actually critiques (availability ≠ capability):
python3 external_critic.py --probe        # scored 0..2 on planted flaws; PASS = ≥1

# 3 · pick and remember your panel (1–3 seats across model families):
python3 external_critic.py --configure    # Enter accepts the suggested free-first panel

# 4 · review real work:
python3 external_critic.py draft.md --panel
```

- **Windows, or no bash:** `python3 critic_setup.py` prints the same setup tailored to your OS and shell (macOS / Linux / Windows; zsh / bash / fish / PowerShell).
- **Cloud seats** (Gemini, GLM, Cloudflare Workers AI, Perplexity, …): store one key per provider — see [API keys](#api-keys). Paid seats always ask before spending.
- No dependencies, ever: `external_critic.py` is Python stdlib only.

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

*Read top to bottom. Every step above is explained in full below* — the [four mandates](#four-mandates-always-on), [Configure to the task](#configure-to-the-task-run-first) (with the floor gate), the Awake stages (**Origin · Spatial · Temporal**), the Sleep stages (**Consolidate · Perturb**) and the [loop structure](#loop-structure), and [Scale](#scale-threads-through-everything). The optional [external critic](#external-critic--probe-pick-run) is the strongest rung of Spatial's independence ladder.

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

- **Map:** diverse critics run *independently* on the original, **each a single contribution** — its raw output is one viewpoint, not a balanced verdict, so balancing them is the panel's job, not the critic's. Independence has a quality ladder by **critic source**: same-context personas (degraded — they anchor on each other) < separate calls to the same model (better) < **a different model** — the **external critic**, run via `external_critic.py` (strongest — uncorrelated errors, an out-of-distribution check). Mix stance — domain-specific and generalist. Add a critic only when it buys a distinct failure surface: **coverage comes from diversity of stance, not headcount** (no fixed number).
- **Reduce — a separate, fresh-context synthesis pass.** Run synthesis in a *fresh context* that consumes the critiques as external inputs — not the context that produced them — so the synthesizer can't anchor on its own map (the one thing a "council" genuinely adds). Here the *synthesis-layer* mandates do their work (preserve-first, steelman): dedupe, rank by leverage (severity×confidence *and* blast radius), surface genuine disagreement as *contested* rather than auto-resolving, emit the preserve-list. With the external reviewer on, **cross-model agreement is strong corroboration and cross-model disagreement is a first-class contested point** — but the external critique is *input, not authority* (mandate 3 governs it).
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

## External critic — probe, pick, run

One model in one session only *approximates* independence (same weights, correlated errors). For a genuinely uncorrelated view, route the artifact to a **different-lineage** model with the bundled, stdlib-only `external_critic.py`. Four commands cover the whole life cycle:

| Command | What it does |
| --- | --- |
| `--probe` | **Certify the seat.** Availability ≠ capability: a reachable model can still be a *null* seat that summarizes instead of critiquing. The probe plants known flaws and scores how many the seat *names* (deterministic grader, no LLM). Results accumulate in a per-machine registry. `--probe-all` scores **every installed local model in one command**, ranked. |
| `--discover` | **List what a key can serve**, newest-first, with cost tier + probe score — so you never hard-code a model that rots. |
| `--configure` | **Pick + remember a panel** of 1–3 capable seats across *distinct* model families (independence = diversity). Enter/`--auto` accepts a score-ranked, free-first suggestion; the choice persists in `critic_panel.json` and new models get flagged on re-runs. |
| `<file> --panel` | **Run the remembered panel.** Every seat critiques the file; each view prints as a *contested* input for your synthesis. Paid seats ask before spending (`--yes` to allow); one dead seat never sinks the panel; every run is pin-logged (model + params) for reproducibility. |

Weight the output by **independence, not authority**: agreement across lineages is strong corroboration; a lone claim is a contested point to surface, not a verdict (mandate 3 governs — reject it where it's wrong). It may *surface* intent-level doubt for you to adjudicate, but cannot settle your goal. Full detail — model selection, the capability probe, the registry, cloud routing — lives in **[EXTERNAL_CRITIC.md](EXTERNAL_CRITIC.md)**.

## API keys

Local Ollama needs **no key**. Cloud seats need one key **per provider**, stored once in your OS secret store under the item `critic-api-key-<provider>` — the helper then finds it by itself (read-only, never printed, never in a dotfile or shell history):

```bash
# each command PROMPTS for the key — nothing lands in your history:
macOS:    security add-generic-password -s critic-api-key-google -a "$USER" -w
Linux:    secret-tool store --label=critic-api-key-google service critic-api-key-google
Windows:  [Environment]::SetEnvironmentVariable("CRITIC_API_KEY_GOOGLE",(Read-Host "key"),"User")
```

Supported providers (each a different lineage from Claude): `openai` · `google` · `deepseek` · `glm` · `mistral` · `cloudflare` · `perplexity` · `ollama-cloud`. Notes:

- **Cloudflare Workers AI** is the budget pick: one key serves **many lineages** (GLM, Kimi, DeepSeek, Qwen, Gemma) with a **free daily allocation**. It also needs your account id (not a secret): `export CLOUDFLARE_ACCOUNT_ID=<id>` — it's in your dashboard URL. Create the token at dash.cloudflare.com → Workers AI → REST API.
- **Windows / Linux:** macOS uses the Keychain; Linux uses libsecret (`secret-tool`); Windows uses per-provider user env vars (Python's stdlib can't read Credential Manager, and the helper stays dependency-free).
- **Subscription CLIs need no key at all:** if the OpenAI **Codex CLI** is on your PATH, it is auto-detected as a `sub` seat (GPT lineage) — it runs on your ChatGPT plan with no per-call bill, so it is *not* spend-gated. Paid **APIs** still ask before every call.
- **A seat with no tokens is not a seat:** when a seat fails on quota (Cloudflare's daily allocation, an unfunded API), the failure is recorded and `--configure` discards it from suggestions (shown as `blocked`) until a re-probe passes.
- An explicit `CRITIC_API_KEY` in the environment always wins; paid seats are **always spend-gated** — `--panel` asks before each paid call.

`python3 critic_setup.py --provider <name>` prints all of this tailored to your OS and shell. Depth (per-OS details, the optional `critic-env` convenience function, static model lists): [EXTERNAL_CRITIC.md](EXTERNAL_CRITIC.md).

---

## Change log

**Self-gated.** From v4.0 on, every version bump must first pass this protocol run on its own spec (preserve-list · three highest-leverage issues · net-improvement gate). **Extension/refactor releases** must also be net lines-removed ≥ lines-added — the standing defense against bloat-on-extension. **Bugfix and explicitly-scoped feature releases are exempt from the line-count test** (a fix or a requested capability can't always shrink the tree), but must still justify every added line and consolidate any prose they touch.

- **v1** — four mandates + stakes tiers + temporal passes.
- **v2** — added Origin and Sleep; named **bloat-on-extension** the standing failure mode (the prune pass became permanent).
- **v3** — evaluated on five adversarial tasks; tiers became *configure-to-the-task* presets; anchoring moved to best-corroborated intent (evolution vs. drift).
- **v3.1** — scale made first-class; outer-loop stop; near-perturbation; schematic + walkthrough.
- **v3.2** — optional **external reviewer** (Ollama): `external_critic.py`, `setup.sh`, the critic-source independence ladder.
- **v3.3** — model guidance made **config-first**: ranked candidate list, installed-first reuse, pin-and-log for reproducibility.
- **v3.4** — **cloud routing** (`CRITIC_BASE_URL` + key, default stays local) and spec-aware local model selection by RAM.
- **v4.0** — first **self-gated** release: honest many-to-many failure lattice; fresh-context synthesis named; setup split into EXTERNAL_CRITIC.md; five-minute start. Net lines removed.
- **v4.1** — cloud-path bug fixed (strict shims reject `seed`); `--depth brief|full`; safe key handling; vendor lineage map.
- **v4.2 / v4.2.1** — **capability probe** `--probe` (availability ≠ capability — a reachable seat can still be null) + per-machine registry; faithful `--probe FILE --expect`; multi-word `--expect` fix.
- **v4.3** — the probe became a **score** (0..N flaws named) that ranks seats; panel of up to 3 across **distinct lineages**, free-first, paid confirm-gated.
- **v4.4** — vendor-neutral guided setup (`critic_setup.py`, cross-platform) + **`--discover`**: list what a key serves, newest-first.
- **v4.5** — **multi-provider keys**: one item per provider + a single `critic-env <provider>` switcher; one panel spans all lineages.
- **v4.6** — **`--configure`**: pick + **remember** a panel (`critic_panel.json`); flags models new since last check; consent-gated `--install`.
- **v4.7** — **`--panel` runs the remembered panel** (spend-gated, endpoint-shape routing, per-seat pin-log); `--select` folded into `--configure`; de-coupled from any host harness.
- **v4.8** — **keys resolve from the OS secret store directly** (bugfix: the docs promised it, but only the optional `critic-env` shell helper delivered it — now `--panel`, `--configure`, *and* plain runs find `critic-api-key-<provider>` on their own; Windows uses per-provider env vars). New providers: **Cloudflare Workers AI** (one key, many lineages, free daily allocation; `CLOUDFLARE_ACCOUNT_ID` fills the per-account URL) and **Perplexity** — both lack `GET /models`, so discovery falls back to a hand-refreshed `STATIC_MODELS` list; multi-lineage providers now infer each seat's lineage from the model id. Lineage table gained gemma/kimi/sonar. **Retired** `gpt-oss:20b` and `deepseek-r1:14b` (reachable but null on real artifacts); `gemma4:12b` promoted (probed 2/2). README reworked: install, API keys, panel life-cycle, concise changelog.
- **v4.9** — closes the two items deferred since v4.0, and widens the capability system. **Abstention channel**: any critic may answer "ABSTAIN: what — why" instead of fabricating; synthesis treats it as a coverage gap, never agreement. **Confidence-term audit**: the three-level vocabulary (corroborated / contested / hypothesis) is now defined once and used consistently — no self-reported percentages. **Probe battery v2**: three planted flaws (contradiction · impossible number · circular order), score 0–3; scores are comparable per battery version. **`--probe-all`**: score every installed local Ollama model in one command, ranked. **Subscription seats**: the OpenAI Codex CLI is auto-detected (`codex-cli` transport, cost tier `sub`, GPT lineage) — plan-covered, keyless, not spend-gated; paid APIs still ask. **Quota-discard**: a seat that fails on quota is recorded and drops out of panel suggestions (`blocked`) until a re-probe passes — a seat with no tokens is not a seat.
