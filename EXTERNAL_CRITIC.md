# External reviewer — setup, model selection, and reproducibility

The optional external reviewer gives the framework a **genuinely independent** viewpoint: a different-lineage model, run on demand, that joins the Spatial panel. Run by one model in one session, the framework's "independent critics" only *approximate* independence — same weights, same context, correlated errors. A different lineage gives uncorrelated errors and an out-of-distribution check. The README's *Optional: external reviewer* section is the two-sentence summary; this file is the full setup.

Helper: `external_critic.py` (dependency-free, stdlib only; returns PRESERVE / ISSUES-or-GENERIC / VERDICT, already shaped to feed synthesis).

## How to weight it

- **What it buys:** agreement with the primary model is strong corroboration; disagreement is a contested point to surface.
- **Independence, not authority.** A local open model is usually weaker. Weight agreement; treat lone external claims skeptically. Mandate 3 (discerning solver) governs — the reviser rejects it where it's wrong.
- **Scope.** It strengthens the *perspective* and *overfitting* axes, and — like any reviewer (see Origin's *doubt the spec*) — may *surface* intent-level doubt (alternative readings, severe tests) for the user to adjudicate; it cannot *unilaterally* confirm meaning, since only the user can settle the goal.
- **Where it runs.** Anywhere the helper can execute — a local Ollama on `localhost:11434`, or outbound HTTPS to a cloud endpoint (`CRITIC_BASE_URL`). It needs a tool-executing context (agentic/CLI), not a hosted chat with no shell.

## Choosing the model

The model is **config-first** (`CRITIC_MODEL`); never hardcode it — the in-script default is only a fallback. Pick a lineage *different from your primary model* (that is what buys the independence), and check `ollama.com/library` for the current tag, since rankings shift monthly:

- **Default / broadly runnable:** `qwen3:8b` — the in-script *floor* (a fallback only); `setup.sh` auto-picks the strongest installed model that safely fits your RAM (see the README changelog for the current benchmarked pick).
- **Stronger general:** `qwen3:14b` / `qwen3:32b`, or a current GLM or DeepSeek tag (verify on `ollama.com/library`).
- **Code review:** a Qwen3-Coder or DeepSeek-Coder tag.

"Auto-update to the newest best model" can't be fully automated — *best* is a human judgment that changes monthly, and there's no clean registry query for it. The achievable design is config-first + a small **ranked preference list** (best first) the setup tries in order — reusing the strongest model you already have, else pulling a light default — refreshed by hand. And for reproducible work (scientific or code), **pin and log** the critic model used for a given review rather than silently auto-bumping mid-run — auto-update to stay current; pin+log (model, seed, params) so a review is auditable and reproducible on the same build (tags are mutable — re-pin after a re-pull). This is the same logged-trace discipline the Temporal axis and the assumptions ledger already use: record which critic produced the critique.

## Setup & test

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
