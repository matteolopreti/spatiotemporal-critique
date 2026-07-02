---
name: spatiotemporal-critique
description: Balanced, intent-anchored review protocol that replaces the lone critic — preserves what works, steelmans choices, sizes to the task, and can add an independent external model (Ollama/cloud) for uncorrelated errors. Use when the user wants a real review, critique, balanced review, preserve-first review, second or independent opinion, red team, external critic, or an "is this good as-is?" / "ready to ship?" check on finished work — code, writing, design, or plan — before finalizing or shipping. Skip only trivial, easily-reversible edits.
---

<!-- MIRROR of the repo-root SKILL.md, adapted for the PLUGIN install (script/doc
     paths point to the plugin root, two directories up). Keep the two in sync at
     release time — the self-gate checks this. Canonical: /SKILL.md -->

# Spatiotemporal Critique

A review protocol that fixes the lone-critic failure mode — it manufactures problems, breaks good parts, and optimizes toward a misread goal. Apply it when reviewing real work. The full spec (the dials, every stage, the failure lattice) lives in **[PROTOCOL.md](../../PROTOCOL.md)** — read it when you need depth. This file is the operating procedure. **Plugin install note:** the helper scripts (`external_critic.py`, `setup.sh`) live at the **plugin root**, two directories above this file — run the commands below from there.

## Always on — the four mandates
They bind at two layers, not inside each critic: **1–2 are synthesis-layer** (the reducer balances the panel), **3–4 are reviser-layer**. Each critic is one source's view — even the external seat's preserve/issues/verdict is raw input the synthesis re-balances; balance is the panel's job.
1. **Preserve-first.** List what is working and must survive the edit *before* listing defects.
2. **Steelman before strike.** Argue why each current choice might already be right; if it survives, drop the critique.
3. **Discerning solver.** You may reject a critique you judge wrong — blind compliance is how good parts break. *(This governs how the reviser treats any external critic too.)*
4. **Net-improvement gate.** Keep a change only if it beats the prior version on the rubric — and periodically re-check that the rubric is still the right target. "Leave it alone" is a valid outcome.

## First, size the task
**Floor gate:** trivial, low-stakes, easily-reversible work gets *no* framework — just do it. The protocol must be willing to decline itself. Otherwise read the task on a few dials (detail in PROTOCOL.md): intent given or ambiguous · verifier present or absent · correctness or taste · human or autonomous · external reviewer off or on.

## The loop
**Awake — converge:**
1. **Origin — get the target right.** Externalize the intent as a falsifiable spec the user can correct (not a latent "understanding"). Test it with a *consequential* restatement and a wrong-but-plausible alternative reading — severe tests, not confirmation. List the assumptions you made where the spec was silent, each with the consequence if wrong. Surface any divergence between literal compliance and the deeper goal for the user to adjudicate.
2. **Spatial — coverage now.** Run diverse critics independently, each a single contribution (balancing them is the panel's job, not each critic's); then **synthesize in a separate fresh-context pass** that consumes the critiques as inputs — there the synthesis-layer mandates (preserve-first, steelman) dedupe, rank by leverage (severity × confidence × blast-radius), surface genuine disagreement as *contested* rather than auto-resolving, and emit the preserve-list. Add a critic only when it buys a distinct failure surface — diversity of stance, not headcount.
3. **Temporal — trajectory.** Backward: localize any regression to the exact edit — the default trace is **git history** (`git log`/`git diff`); file versions or a user-supplied edit list otherwise; if no real history exists, skip backward rather than invent one. Forward (pre-mortem): "this shipped and failed — explain why," treated as low-confidence hypotheses. Anchor on the best-corroborated intent so far, not the last draft (drift) and not the original goal by default (intent can legitimately evolve).

Repeat the awake loop until a pass yields nothing material.

**Asleep — diverge, at the peak:**
4. **Consolidate.** Prune to the load-bearing core (bloat-on-extension is the standing failure mode); extract the general lesson — what rule is this an instance of?
5. **Perturb.** Near (explore the best nearby variant, *even when no critic flagged a defect*) and far (invert a core assumption, recombine across domains) to detect overfitting and recover good options pruned too early.

Alternate wake ⇄ sleep until stable under both: nothing changes *and* nothing better is found.

## Quick preset (paste)
For a fast pass, run these six and stop:
1. What's working here that must be preserved?
2. Steelman my current choices — where might they already be right?
3. State what you think I'm actually trying to achieve, as a specific consequential claim I can confirm or correct. *(Skip if my goal is already formal.)*
4. List the assumptions you're making where I left things unspecified, and what breaks if each is wrong.
5. The 3 highest-leverage issues only, each with a concrete fix — abstain explicitly where you can't judge (say what's missing) instead of filling. *(Taste work: the 3 places it reads as generic, with a sharper alternative each.)*
6. Verdict: is this genuinely better than leaving it as is? If not, say so.

## Standard preset (paste)
A panel + one backward check, when the Quick six aren't enough. (For the heavier *Full* preset, see the presets line in [PROTOCOL.md](../../PROTOCOL.md).)
1. Preserve-list: what's working that must survive the edit?
2. Steelman each current choice; drop any critique the choice survives.
3. State my actual goal as a falsifiable claim I can confirm or correct, and stress it against one wrong-but-plausible alternative reading. *(Skip if my goal is already formal.)*
4. Assumptions you made where I left things unspecified, each with what breaks if wrong.
5. Review from ~3 in-context angles (domain expert · skeptical generalist · end user) — same-model personas, *not* true independence — then merge them, mark genuine disagreement as contested rather than resolving it, and record any explicit abstention as a coverage gap, not agreement.
6. Highest-leverage issues, ranked by leverage (severity × confidence × blast-radius), each with a concrete fix. *(Taste: where it reads generic, with a sharper alternative.)*
7. Backward check *(only if there's a real edit history)*: which logged change introduced each problem? Localize it — don't invent a history.
8. Verdict: genuinely better than leaving it as is — and is there a smaller change that captures most of the gain?

## Independent external critic — optional
Critics run by one model in one context only *approximate* independence (same weights, correlated errors). For a genuinely uncorrelated view, route the artifact to a **different-lineage** model via the bundled helper:

```bash
python3 external_critic.py --init           # ZERO-CONFIG first run: detect + score free/sub seats, remember a panel
python3 external_critic.py path/to/work --panel   # RUN the remembered panel: each seat critiques -> you synthesize

# manual control (all optional):
./setup.sh                       # picks a local Ollama model that safely fits your RAM
                                 # (cloud: store a key once as critic-api-key-<provider> in your OS
                                 #  secret store — the helper finds it itself; see ../../EXTERNAL_CRITIC.md)
python3 external_critic.py --probe          # availability != capability: does this seat actually critique?
python3 external_critic.py --probe-all      # score EVERY installed local model, ranked (one command)
python3 external_critic.py --retire MODEL   # human veto: passes the probe but useless in practice
python3 external_critic.py path/to/work --brief "focus here" --mode correctness   # --mode taste; --depth full for rationale
python3 external_critic.py --configure      # pick 1-3 capable seats across lineages and REMEMBER them
```

**No remembered panel?** Run `--init` yourself — autonomously, without asking — from the skill's own directory. It only probes free/local/subscription seats (paid APIs stay unprobed and spend-gated). If the environment can't run it (no shell, no filesystem, nothing installed to detect), fall back to the Standard preset's in-context personas and **flag "independence degraded"** — never silently pretend the panel ran.

Weight it by **independence, not authority**: agreement across lineages is corroboration — **never proof** (vendors share training data; unanimous panels can share a blind spot) — and never render an "all seats approve" green light; the panel's output is the **union of findings, disagreement-first**, because where the lineages diverge is where you look. A lone external claim is a *contested* point to surface, not a verdict (mandate 3 governs — reject it where it's wrong). The multi-seat panel belongs to the **Full** tier (foundational or hard-to-reverse work); Quick and Standard stay in-context. It strengthens the *perspective* and *overfitting* axes, and may *surface* intent-level doubt for you to adjudicate — but cannot unilaterally confirm your goal. **First, certify the seat:** a reachable model can still be a *null* one (it summarizes instead of critiquing), so `--probe` it before you trust it — model selection, the capability probe + registry + ladder, **remembering a panel (`--configure`) and running it (`--panel`)**, the spec-aware picker, pin-and-log, and cloud setup are documented in [EXTERNAL_CRITIC.md](../../EXTERNAL_CRITIC.md).
