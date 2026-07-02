# Spatiotemporal Critique

[![Release](https://img.shields.io/github/v/release/matteolopreti/spatiotemporal-critique)](https://github.com/matteolopreti/spatiotemporal-critique/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Claude skill](https://img.shields.io/badge/Claude-skill-d97757)](SKILL.md)
[![External critic: Ollama or cloud](https://img.shields.io/badge/external%20critic-Ollama%20%7C%20cloud-555)](EXTERNAL_CRITIC.md)

**Spatiotemporal Critique is a free, open-source [Claude Code](https://www.claude.com/product/claude-code) skill for balanced AI code and writing review.** Instead of one model hunting for flaws — inventing problems, missing what you actually wanted, breaking what already worked — it runs a structured, **preserve-first** review protocol, and can add a **genuinely independent second opinion from a different model family** (a local Ollama model, the Codex CLI on your subscription, or Gemini / GLM / DeepSeek in the cloud), so the review isn't the same model critiquing itself.

*The name, decoded:* **spatial** = several independent angles on the work as it stands; **temporal** = checking the history of edits for what broke and what's about to.

**Get it as a Claude Code skill — one command:**

```bash
git clone https://github.com/matteolopreti/spatiotemporal-critique ~/.claude/skills/spatiotemporal-critique
```

Restart Claude Code and ask: *"give me a real review of this before I ship it."* Prefer plugins? `/plugin marketplace add matteolopreti/spatiotemporal-critique`, then `/plugin install spatiotemporal-critique@spatiotemporal-critique`. No Python package dependencies — markdown + stdlib Python (the optional external panel additionally needs a local Ollama model, an agent CLI you already have, or a cloud key). Not on Claude Code? The protocol works as a pasted prompt with any AI assistant — presets in [SKILL.md](SKILL.md).

The lone critic fails in several overlapping ways; the framework answers them **many-to-many** — one failure can need several stages, and one stage can answer several failures (every mechanism named here is defined in the full spec, [PROTOCOL.md](PROTOCOL.md)):

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

**And here it is for real** — a GPT-lineage panel seat reviewing *this repo's own v4.10 release diff* (releases self-gate through the panel; output verbatim, trimmed):

```text
=== PANEL CRITIC: codex-default [gpt]  (codex-cli) ===
1. PRESERVE — `CLI_SEATS` is the right direction: Codex/Gemini are centralized,
   CRITIC_MODEL is prevented from leaking into CLI `-m`, and endpoint-keyed
   registry records preserve "same model id, different transport" separation.
2. ISSUES —
[severity high] `--init` can save a failed/null seat — `_candidate_rows()` maps a
   latest FAIL to "unprobed", so a seat that just failed the probe can still be
   suggested and written. Fix: represent FAIL as "failed" and exclude it.
[severity high] `--retire MODEL` is not a reliable veto — records are keyed
   (model, endpoint) but do_retire() writes only to the current endpoint.
VERDICT — not good as-is: the design is sound, but the FAIL→unprobed path can
   make the zero-config bootstrap remember a bad seat.
```

Four of its five findings were accepted and fixed before the release shipped; one was rejected after steelmanning — which is exactly the protocol working (mandate 3: the reviser may reject a critique it judges wrong).

---

## Install

**As a Claude Code skill (recommended):** the one-command clone at the top of this page, or the plugin marketplace (`/plugin marketplace add matteolopreti/spatiotemporal-critique`). Claude matches on it automatically whenever you ask for a real review, critique, or second opinion. **No Claude Code?** Nothing to install at all — paste the presets from [SKILL.md](SKILL.md) into any AI assistant.

**The external critic panel** (optional, what makes the second opinion *independent*) is a small stdlib-only Python helper:

```bash
cd ~/.claude/skills/spatiotemporal-critique   # or wherever you cloned it

# 1 · zero-config: detect + score everything this machine can field, remember a panel.
#     (local Ollama models, and the codex / gemini CLIs if you have them — free/sub only)
python3 external_critic.py --init

# 2 · review real work:
python3 external_critic.py draft.md --panel
```

That's the whole onboarding. Optional extras:

- **No local model yet?** `./setup.sh` picks one that fits your RAM (asks before pulling); `python3 critic_setup.py` prints the same tailored to any OS/shell (macOS / Linux / Windows; zsh / bash / fish / PowerShell).
- **Cloud seats** (Gemini, GLM, Cloudflare Workers AI, Perplexity, …): store one key per provider — see [API keys](#api-keys). Paid seats always ask before spending; `--init` never probes them.
- **Manual control:** `--probe` (certify one seat) · `--probe-all` (rank all local models) · `--configure` (pick your own panel) · `--retire` (veto a seat that passes the probe but is useless in practice).
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

*Every step above is specified in full in **[PROTOCOL.md](PROTOCOL.md)*** — the four mandates, Configure-to-the-task (with the floor gate), the Awake stages (**Origin · Spatial · Temporal**), the Sleep stages (**Consolidate · Perturb**), the loop structure, and Scale. The optional [external critic](#external-critic--probe-pick-run) below is the strongest rung of Spatial's independence ladder.

---

## External critic — probe, pick, run

One model in one session only *approximates* independence (same weights, correlated errors). For a genuinely uncorrelated view, route the artifact to a **different-lineage** model with the bundled, stdlib-only `external_critic.py`. Four commands cover the whole life cycle:

| Command | What it does |
| --- | --- |
| `--init` | **Zero-config bootstrap** — *of what's already on the machine*: it detects and scores local Ollama models and subscription CLIs (codex, gemini) and remembers the suggested panel — one command, no choices, never two seats from one model family, never a Claude-lineage seat. It selects; it doesn't provision — you bring at least one local model, CLI, or key. Paid APIs are never auto-probed. |
| `--probe` | **Floor-certify the seat.** Availability ≠ capability: a reachable model can still be a *null* seat that summarizes instead of critiquing. The probe plants known flaws and scores how many the seat *names* (deterministic grader, no LLM) — a **floor**, not a full warranty (a seat can pass small and still null on large artifacts; the faithful probe and `--retire` cover that gap). Results accumulate in a per-machine registry. `--probe-all` scores **every installed local model in one command**, ranked. `--retire MODEL` is the human veto for a seat that passes the probe but proves useless in practice. |
| `--discover` | **List what a key can serve**, newest-first, with cost tier + probe score — so you never hard-code a model that rots. |
| `--configure` | **Pick + remember a panel** of 1–3 capable seats across *distinct* model families (independence = diversity). Enter/`--auto` accepts a score-ranked, free-first suggestion; the choice persists in `critic_panel.json` and new models get flagged on re-runs. |
| `<file> --panel` | **Run the remembered panel.** Every seat critiques the file; each view prints as a *contested* input for your synthesis. Paid seats ask before spending (`--yes` to allow); one dead seat never sinks the panel; every run is pin-logged (model + params) for reproducibility. |

Weight the output by **independence, not authority**: agreement across lineages is corroboration — never proof; a lone claim is a contested point to surface, not a verdict (mandate 3 governs — reject it where it's wrong). It may *surface* intent-level doubt for you to adjudicate, but cannot settle your goal. Full detail — model selection, the capability probe, the registry, cloud routing — lives in **[EXTERNAL_CRITIC.md](EXTERNAL_CRITIC.md)**.

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
- **Subscription CLIs need no key at all:** the OpenAI **Codex CLI** (GPT lineage, ChatGPT plan) and the **Gemini CLI** (Gemini lineage, Google login — authenticate once by running `gemini`) are auto-detected as `sub` seats with no per-call bill, so they are *not* spend-gated. Paid **APIs** still ask before every call.
- **A seat with no tokens is not a seat:** when a seat fails on quota (Cloudflare's daily allocation, an unfunded API), the failure is recorded and `--configure` discards it from suggestions (shown as `blocked`) until a re-probe passes.
- An explicit `CRITIC_API_KEY` in the environment always wins; paid seats are **always spend-gated** — `--panel` asks before each paid call.

`python3 critic_setup.py --provider <name>` prints all of this tailored to your OS and shell. Depth (per-OS details, the optional `critic-env` convenience function, static model lists): [EXTERNAL_CRITIC.md](EXTERNAL_CRITIC.md).

---

## FAQ

### Is this a Claude Code skill or a prompt I paste?

Both. Cloned into `~/.claude/skills/` (or installed via the plugin marketplace), it's a native Claude Code skill — Claude applies the protocol automatically when you ask for a review. Without Claude Code, the [Quick and Standard presets](SKILL.md) are self-contained prompts that work pasted into any AI assistant.

### How do I get an AI code review that isn't one-sided?

The one-sided review is a *structural* problem: a critic prompted only to find flaws will find flaws, real or not. This protocol makes balance structural instead — the reviewer must first list what works and must survive the edit (preserve-first), argue for your existing choices before striking them (steelman), and is allowed to conclude "leave it alone."

### What makes the second opinion actually independent?

Lineage. Two calls to the same model share the same weights and the same blind spots — same-lineage agreement is close to no evidence. The panel routes your work to *different model families* (Gemma/Gemini, GPT, GLM, DeepSeek…), certifies each seat with a deterministic capability probe before trusting it, and treats cross-lineage agreement as corroboration and disagreement as a flagged, contested point. The suggested panel is *structurally* diverse: it never picks two seats from one family, and never a Claude-lineage seat. Every trust claim here is verifiable by command — see the [trust contract](EXTERNAL_CRITIC.md#trust-contract--verify-every-claim-yourself).

### Is it free? Does it work offline?

Yes and yes. A local Ollama model costs nothing and nothing leaves your machine; the OpenAI Codex CLI rides a subscription you may already have. Cloud API seats are optional, keyed per provider from your OS secret store, and every paid call asks first.

### What if the external critic disagrees with Claude?

Disagreement is signal, not a verdict. The synthesis surfaces it as a *contested point* for you to weigh — the external critique is input, never authority, and the reviser may reject it where it's wrong (mandate 3). A critic can also explicitly **abstain** rather than fabricate a finding; that's reported as a coverage gap, not agreement.

---

## Docs

- **[PROTOCOL.md](PROTOCOL.md)** — the full framework specification (mandates, dials, Awake/Sleep stages, loop structure, scale).
- **[SKILL.md](SKILL.md)** — the operating procedure, with the Quick and Standard paste presets.
- **[EXTERNAL_CRITIC.md](EXTERNAL_CRITIC.md)** — external-model setup: capability probe, registry, API keys, cloud routing, the trust contract.
- **[TRIAL.md](TRIAL.md)** — measured results: the protocol vs. a lone critic, and the panel, on a planted-defect battery (raw responses committed; re-score them yourself).
- **[CHANGELOG.md](CHANGELOG.md)** — full version history (self-gated releases, v1 → current).
- **[ROADMAP.md](ROADMAP.md)** — what's next, and the v5.0 gate.
