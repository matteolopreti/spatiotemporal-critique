# External reviewer — setup, model selection, and reproducibility

The optional external reviewer gives the framework a **genuinely independent** viewpoint: a different-lineage model, run on demand, that joins the Spatial panel. Run by one model in one session, the framework's "independent critics" only *approximate* independence — same weights, same context, correlated errors. A different lineage gives uncorrelated errors and an out-of-distribution check. The README's *Optional: external reviewer* section is the two-sentence summary; this file is the full setup.

Helper: `external_critic.py` (dependency-free, stdlib only; returns PRESERVE / ISSUES-or-GENERIC / VERDICT, already shaped to feed synthesis).

## How to weight it

- **Independence, not authority.** Agreement with the primary model is strong corroboration; a lone external claim (an open model is usually weaker) is a contested point to surface, not a verdict. Mandate 3 (discerning solver) governs — the reviser rejects it where it's wrong.
- **Scope.** It strengthens the *perspective* and *overfitting* axes, and — like any reviewer (see Origin's *doubt the spec*) — may *surface* intent-level doubt (alternative readings, severe tests) for the user to adjudicate; it cannot *unilaterally* confirm meaning, since only the user can settle the goal.
- **Where it runs.** Anywhere the helper can execute — a local Ollama on `localhost:11434`, or outbound HTTPS to a cloud endpoint (`CRITIC_BASE_URL`). It needs a tool-executing context (agentic/CLI), not a hosted chat with no shell.

## Choosing the model

The model is **config-first** (`CRITIC_MODEL`); never hardcode it — the in-script default is only a fallback. Pick a lineage *different from your primary model* (that is what buys the independence), and check `ollama.com/library` for the current tag, since rankings shift monthly:

- **Default / broadly runnable:** `qwen3:8b` — the in-script *floor* (a fallback only); `setup.sh` auto-picks the strongest installed model that safely fits your RAM (see the README changelog for the current benchmarked pick).
- **Stronger general:** `qwen3:14b` / `qwen3:32b`, or a current GLM or DeepSeek tag (verify on `ollama.com/library`).
- **Code review:** a Qwen3-Coder or DeepSeek-Coder tag.

**Cloud (with an API key): pick by lineage, not by leaderboard.** The point is independence *from your primary model*, so reach by vendor family — each a different lineage from Claude — and confirm the current tag on the vendor's own model page. A hardcoded "best N" list rots within weeks, so the durable guidance is the families, not the tags:

| API / vendor | Lineage (≠ Claude) | Endpoint base |
|---|---|---|
| Google AI Studio | Gemini | `…/v1beta/openai` (OpenAI-compat) |
| OpenAI | GPT | `…/v1` |
| DeepSeek | DeepSeek | OpenAI-compat; cheap, strong code lineage |
| Z.ai | GLM | `…/api/paas/v4` |
| Mistral | Mistral | OpenAI-compat; EU-hosted |

*Current picks (as of 2026-06 — perishable, verify before trusting): `gemini-3.1-pro-preview`, a current `gpt-…`, a `deepseek-…` tag, `glm-5.2`. Refresh this one line by hand; the table above is the part that lasts.*

"Auto-update to the newest best model" can't be fully automated — *best* is a human judgment that changes monthly, and there's no clean registry query for it. The achievable design is config-first + a small **ranked preference list** (best first) the setup tries in order — reusing the strongest model you already have, else pulling a light default — refreshed by hand. And for reproducible work (scientific or code), **pin and log** the critic model used for a given review rather than silently auto-bumping mid-run — auto-update to stay current; pin+log (model, seed, params) so a review is auditable and reproducible on the same build (tags are mutable — re-pin after a re-pull). This is the same logged-trace discipline the Temporal axis and the assumptions ledger already use: record which critic produced the critique.

## Setup & test

```bash
# one-time, guided setup (installs nothing unless you pass --install)
chmod +x setup.sh external_critic.py
./setup.sh

# run it on a real file (add --depth full for a rationale per finding on high-stakes work)
python3 external_critic.py path/to/draft.md --brief "focus here" --mode correctness

# for code review, point at a current code model of a different lineage
# (verify the tag on ollama.com/library — these move monthly):
CRITIC_MODEL=qwen3-coder ./setup.sh

# or route to a hosted, different-lineage model — see "Cloud routing" below
# (the artifact leaves your machine, and the key must stay out of your history).
```

`setup.sh` writes its pick to `.env` for the helper and asks before any pull; `external_critic.py` logs the model and sampling params used on every run (`critique.log`, next to the helper; `--no-log` to skip) so a review is auditable. (`seed` is logged for local Ollama, where it's honored; cloud endpoints don't take it, so it logs as `na`.)

## Cloud routing — and keeping the key out of your shell history

Cloud mode is fully env-driven: set `CRITIC_BASE_URL` (+ `CRITIC_MODEL`, and `CRITIC_API_KEY` for keyed endpoints) and the same helper routes there. The trap is the **key**: an inline `export CRITIC_API_KEY=sk-…` lands in your shell history, and putting it in `.env` lands it on disk. Store it once in your OS secret store and load it into the env *only for the run*:

```bash
# store the key once (prompts; nothing written to a dotfile or to history):
#   macOS:  security add-generic-password -s gemini-critic-key -a "$USER" -w
#   Linux:  secret-tool store --label=gemini-critic-key service gemini-critic-key   # or use `pass`

# a reusable shell function (in ~/.zshrc) that loads endpoint + key just-in-time:
critic-env() {                                  # usage: critic-env [model]
  export CRITIC_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai"
  export CRITIC_MODEL="${1:-gemini-3.1-pro-preview}"
  export CRITIC_API_KEY="$(security find-generic-password -s gemini-critic-key -w 2>/dev/null)"
  #   Linux: CRITIC_API_KEY="$(secret-tool lookup service gemini-critic-key)"
  [ -n "$CRITIC_API_KEY" ] && echo "critic-env ready: $CRITIC_MODEL" || echo "WARN: key not in keychain" >&2
}

critic-env                                                            # load for this shell
python3 external_critic.py draft.md --mode correctness               # terse (default)
python3 external_critic.py draft.md --mode correctness --depth full  # +rationale, high-stakes
```

Swap the base URL and key item per vendor (see the lineage map above). The key then lives only in the secret store and in this one shell's env — never in a file or your history. The helper sends only widely-supported request fields on this path (e.g. it omits `seed`, which strict OpenAI-compat shims like Gemini's reject), and surfaces the endpoint's own error text if a request is refused.

For a **published skill**, automate *detection and guidance*, not silent installation: when the user turns the reviewer on, run the preflight; if Ollama isn't ready, report the one command (`./setup.sh`) and the approximate download size, and leave installing/pulling to explicit consent. Never silently install software or pull multi-GB models on a user's machine.
