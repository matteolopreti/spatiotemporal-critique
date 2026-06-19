---
name: spatiotemporal-critique
description: Balanced, intent-anchored review protocol that replaces the one-sided "critic persona" — it preserves what works, steelmans the current choices, sizes itself to the task, and can pull in a genuinely independent external model (local Ollama, or a cloud OpenAI-compatible endpoint) for uncorrelated errors. Use this whenever the user wants a real review, critique, or "is this good as-is?" check on work they have made — code, writing, a design, a plan — especially before finalizing or shipping, when they want both what is wrong AND what is right, want a second or independent opinion, or mention "balanced review", "preserve-first", a "red team", or an "external critic". Prefer it over ad-hoc nitpicking for any finished or near-finished artifact; skip it only for trivial, easily-reversible edits.
---

# Spatiotemporal Critique

A review protocol that fixes the lone-critic failure mode — it manufactures problems, breaks good parts, and optimizes toward a misread goal. Apply it when reviewing real work. The full spec (schematic, dials, every stage, the change log) lives in **[README.md](README.md)** — read it when you need depth. This file is the operating procedure.

## Always on — the four mandates
1. **Preserve-first.** List what is working and must survive the edit *before* listing defects.
2. **Steelman before strike.** Argue why each current choice might already be right; if it survives, drop the critique.
3. **Discerning solver.** You may reject a critique you judge wrong — blind compliance is how good parts break. *(This governs any external critic too.)*
4. **Net-improvement gate.** Keep a change only if it beats the prior version on the rubric — and periodically re-check that the rubric is still the right target. "Leave it alone" is a valid outcome.

## First, size the task
**Floor gate:** trivial, low-stakes, easily-reversible work gets *no* framework — just do it. The protocol must be willing to decline itself. Otherwise read the task on a few dials (detail in README): intent given or ambiguous · verifier present or absent · correctness or taste · human or autonomous · external reviewer off or on.

## The loop
**Awake — converge:**
1. **Origin — get the target right.** Externalize the intent as a falsifiable spec the user can correct (not a latent "understanding"). Test it with a *consequential* restatement and a wrong-but-plausible alternative reading — severe tests, not confirmation. List the assumptions you made where the spec was silent, each with the consequence if wrong.
2. **Spatial — coverage now.** Run diverse, *independent* critics; dedupe and rank by leverage (severity × confidence × blast-radius); surface genuine disagreement as *contested* rather than auto-resolving; emit the preserve-list.
3. **Temporal — trajectory.** Backward: localize any regression to the exact edit. Forward (pre-mortem): "this shipped and failed — explain why," treated as low-confidence hypotheses. Anchor on the best-corroborated intent so far, not the last draft (drift) and not the original goal by default (intent can legitimately evolve).

Repeat the awake loop until a pass yields nothing material.

**Asleep — diverge, at the peak:**
4. **Consolidate.** Prune to the load-bearing core (bloat-on-extension is the standing failure mode); extract the general lesson — what rule is this an instance of?
5. **Perturb.** Near (explore the best nearby variant, *even when no critic flagged a defect*) and far (invert a core assumption, recombine across domains) to detect overfitting and recover good options pruned too early.

Alternate wake ⇄ sleep until stable under both: nothing changes *and* nothing better is found.

## Quick version — paste-and-go
For a fast pass, run these six and stop:
1. What's working here that must be preserved?
2. Steelman my current choices — where might they already be right?
3. State what you think I'm actually trying to achieve, as a specific consequential claim I can confirm or correct. *(Skip if my goal is already formal.)*
4. List the assumptions you're making where I left things unspecified, and what breaks if each is wrong.
5. The 3 highest-leverage issues only, each with a concrete fix. *(Taste work: the 3 places it reads as generic, with a sharper alternative each.)*
6. Verdict: is this genuinely better than leaving it as is? If not, say so.

## Independent external critic — optional
Critics run by one model in one context only *approximate* independence (same weights, correlated errors). For a genuinely uncorrelated view, route the artifact to a **different-lineage** model via the bundled helper:

```bash
./setup.sh                       # one-time: picks a local model that safely fits your RAM
                                 # (or export CRITIC_BASE_URL + CRITIC_API_KEY for a cloud endpoint)
python3 external_critic.py path/to/work --brief "focus here" --mode correctness   # or --mode taste
```

Weight it by **independence, not authority**: agreement with your own review is strong corroboration; a lone external claim is a *contested* point to surface, not a verdict (mandate 3 governs — reject it where it's wrong). It strengthens the *perspective* and *overfitting* axes, **not** the *intent* axis — only the user knows their goal. Model selection, the spec-aware picker, pin-and-log, and cloud setup are documented in [README.md](README.md).
