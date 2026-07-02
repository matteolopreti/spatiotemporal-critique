# External reviewer — setup, model selection, and reproducibility

The optional external reviewer gives the framework a **genuinely independent** viewpoint: a different-lineage model, run on demand, that joins the Spatial panel. Run by one model in one session, the framework's "independent critics" only *approximate* independence — same weights, same context, correlated errors. A different lineage gives uncorrelated errors and an out-of-distribution check. The README's *Optional: external reviewer* section is the two-sentence summary; this file is the full setup.

Helper: `external_critic.py` (dependency-free, stdlib only; returns PRESERVE / ISSUES-or-GENERIC / VERDICT, already shaped to feed synthesis).

## How to weight it

- **Independence, not authority.** Agreement with the primary model is strong corroboration; a lone external claim (an open model is usually weaker) is a contested point to surface, not a verdict. Mandate 3 (discerning solver) governs — the reviser rejects it where it's wrong.
- **Scope.** It strengthens the *perspective* and *overfitting* axes, and — like any reviewer (see Origin's *doubt the spec*) — may *surface* intent-level doubt (alternative readings, severe tests) for the user to adjudicate; it cannot *unilaterally* confirm meaning, since only the user can settle the goal.
- **Where it runs.** Anywhere the helper can execute — a local Ollama on `localhost:11434`, or outbound HTTPS to a cloud endpoint (`CRITIC_BASE_URL`). It needs a tool-executing context (agentic/CLI), not a hosted chat with no shell.

## Choosing the model

The model is **config-first** (`CRITIC_MODEL`); never hardcode it — the in-script default is only a fallback. Pick a lineage *different from your primary model* (that is what buys the independence), and check `ollama.com/library` for the current tag, since rankings shift monthly:

- **Default / broadly runnable:** `qwen3:8b` — the in-script *floor* (a fallback only); `setup.sh` auto-picks the strongest installed model that safely fits your RAM.
- **Stronger general:** `gemma4:12b` (probed **2/2** here — the current best local pick), `qwen3:14b` / `qwen3:32b`, or a current GLM tag (verify on `ollama.com/library`).
- **Code review:** a Qwen3-Coder or DeepSeek-Coder tag.
- **Retired (2026-07):** `gpt-oss:20b` and `deepseek-r1:14b` — reachable but **null on real artifacts** (they summarized instead of critiquing; that failure is exactly what the capability section below detects).

**Cloud (with an API key): pick by lineage, not by leaderboard.** The point is independence *from your primary model*, so reach by vendor family — each a different lineage from Claude — and confirm the current tag on the vendor's own model page. A hardcoded "best N" list rots within weeks, so the durable guidance is the families, not the tags:

| API / vendor | Lineage (≠ Claude) | Endpoint base |
|---|---|---|
| Google AI Studio | Gemini (+ Gemma) | `…/v1beta/openai` (OpenAI-compat) |
| OpenAI | GPT | `…/v1` |
| DeepSeek | DeepSeek | OpenAI-compat; cheap, strong code lineage |
| Z.ai | GLM | `…/api/paas/v4` |
| Mistral | Mistral | OpenAI-compat; EU-hosted |
| Cloudflare Workers AI | *many* — GLM, Kimi, DeepSeek, Qwen, Gemma | `…/accounts/<id>/ai/v1` (OpenAI-compat; **free daily allocation**, then paid; needs `CLOUDFLARE_ACCOUNT_ID`) |
| Perplexity | Sonar | `https://api.perplexity.ai` (OpenAI-compat) |

Cloudflare and Perplexity serve **no `GET /models`**, so `--discover`/`--configure` fall back to a small hand-refreshed candidate list in `critic_providers.py` (`STATIC_MODELS`) — refresh it when the vendors rotate models. Cloudflare is notable as **one key that serves many distinct lineages** (the panel infers each seat's lineage from the model id, so a Cloudflare GLM and a Cloudflare Kimi count as two families).

*Current picks (as of 2026-07 — perishable, verify before trusting): `gemini-3.5-flash`; via Cloudflare `@cf/zai-org/glm-5.2`, `@cf/moonshotai/kimi-k2.7-code` (code), `@cf/deepseek-ai/deepseek-r1-distill-qwen-32b`; `sonar-pro`. Refresh this one line by hand; the table above is the part that lasts.*

"Auto-update to the newest best model" can't be fully automated — *best* is a human judgment that changes monthly, and there's no clean registry query for it. The achievable design is config-first + a small **ranked preference list** (best first) the setup tries in order — reusing the strongest model you already have, else pulling a light default — refreshed by hand. And for reproducible work (scientific or code), **pin and log** the critic model used for a given review rather than silently auto-bumping mid-run — auto-update to stay current; pin+log (model, seed, params) so a review is auditable and reproducible on the same build (tags are mutable — re-pin after a re-pull). This is the same logged-trace discipline the Temporal axis and the assumptions ledger already use: record which critic produced the critique.

## Capability detection — availability ≠ capability

A reachable seat is not a capable one. A model can answer every request yet add **no real check** — it regenerates or summarizes the artifact instead of finding its flaw. That is *independence-theater*: it looks like a second opinion while sharing none of the work. Observed, on the bytes: `gpt-oss:20b` and `deepseek-r1:14b` were both reachable, but on the two-flaw probe `gpt-oss` scored **2/2** (named both), `deepseek` only **1/2** (caught the impossible number, **missed the contradiction**), and a different local seat had *endorsed* a contradictory claim as something to preserve. Reachability told you nothing; you have to *test the seat* — and the score *ranks* the ones that pass.

So the helper applies its own discipline — the **planted defect** — to the critic seat itself:

```bash
python3 external_critic.py --probe                 # FLOOR probe — scored 0..N (built-in artifact)
python3 external_critic.py --probe FILE --expect "contradict,inconsistent,false"   # FAITHFUL probe
python3 external_critic.py --configure             # PICK 1-3 across lineages and REMEMBER them (--auto for the suggestion)
python3 external_critic.py draft.md --panel        # RUN the remembered panel (each seat critiques)
```

- **Floor probe (`--probe`, default) — now scored.** Feeds the configured seat a tiny artifact with **two independent, blatant flaws** (a contradiction + an impossible number) and returns a **capability SCORE = how many it NAMES** (0..N) with a **deterministic, non-LLM** grader. Because diagnosis vocabulary is open-ended, the grader doesn't match per-flaw wordlists (that false-missed capable seats); a flaw is *named* when some sentence — or an adjacent pair — pairs that flaw's **subject anchor** with any **fault word**, so a restating summary scores 0. A `<think>…</think>` block is stripped so the *answer* is graded. **PASS = score ≥ 1** (genuine critique) · **score = 0 → FAIL** (a null seat) · **UNAVAILABLE** = it never answered (unreachable, or a stale id — the `…-preview` 400). The score *ranks* the panel; a misrank only reorders (cheap), so the gate stays binary.
- **Faithful probe (`--probe FILE --expect "…"`).** The floor probe is *necessary, not sufficient*: capability is **artifact-dependent**. `gpt-oss` passes the tiny probe yet summarized a multi-section governance bundle — a tiny probe can't predict a large/abstract one. So for high-stakes work, plant **one** known flaw in a *slice of your real artifact* and name the word(s) a genuine critic must say (`--expect`, multi-word phrases allowed); the grader checks the seat caught it. This is the rung that catches **scale/abstraction-induced** nulling.
- **Registry (`critic_registry.tsv`, next to `critique.log`).** Every probe appends `{date · model · lineage · probe · score · cost · note}`; the **newest record per model** wins, so a capable seat is reused, not re-probed — and a PASS older than ~30 days is flagged **stale** (tags mutate; re-probe). Gitignored, per-machine.
- **Panel (`--configure` → `--panel`).** `--configure` builds a panel of up to **3 capable seats across DISTINCT lineages** — independence is *diversity* (three of one family share a blind spot) — so it groups candidates by lineage and **suggests** the best-scoring seat per lineage, **free-first** (accept with Enter or `--auto`; or pick your own 1–3). Free seats are usable now; a **paid** seat is listed UNPROBED and **`--panel` asks before spending** (never auto-spent). None capable → fall back to a same-lineage in-context reviewer (the Standard preset's personas, or a host harness's `decorrelated-reviewer`), **flagged "independence degraded."** Hunt more **free + capable** lineages by probing each free option (local Ollama + free-tier cloud); the panel widens as you do. Then **`--panel <file>`** runs every remembered seat and prints each view as a *contested* input for synthesis.
- **A normal critique run** prints a one-line **advisory** when the chosen model has no capability-PASS on record (or a stale one) — non-blocking; it nudges you to `--probe` first.

**The boundary that does not move.** A PASS certifies the seat **genuinely critiques** — it improves the *read*. It does **not** grant authority over whether the *goal* is right: that residual is the user's, and no seat (capable or not) can take it. Auto-**excluding** a null seat is legitimate because the grader is a *different substrate* (deterministic, not an LLM judgment); **trusting** a seat's verdict is still weighted by independence, never authority (Mandate 3 governs). And the floor probe's own residual — a seat that passes small yet nulls large — is why the seat stays advisory and **you still read its first real critique.**

## Setup & test

**Guided, cross-platform (recommended):** `critic_setup.py` detects your OS, shell, and RAM and prints a tailored, copy-pasteable setup — the best local Ollama model for your RAM, *or* safe key storage + a `critic-env` snippet for *your* shell. Detection + guidance only: it stores nothing, installs nothing, and pulls nothing on its own. (Opt-in: `critic_setup.py --install` *appends* the `critic-env` function to your shell rc — consent-gated, idempotent, one upfront prompt; `--yes` for non-interactive.)

```bash
python3 critic_setup.py                      # local Ollama (free) — picks a model for your RAM
python3 critic_setup.py --provider list      # the cloud providers (each a different lineage)
python3 critic_setup.py --provider openai    #   or  google | deepseek | glm | mistral | cloudflare | perplexity | ollama-cloud

# certify a seat really critiques, discover what a cloud key can serve, then build the panel:
python3 external_critic.py --probe                          # SCORE this seat (0..N); PASS = >=1
python3 external_critic.py --discover                       # (cloud) models this key can serve, newest-first + score
python3 external_critic.py --configure                      # PICK 1-3 across lineages and REMEMBER them (critic_panel.json; --auto for the suggestion)

# run a review (add --depth full for a rationale per finding on high-stakes work):
python3 external_critic.py path/to/draft.md --brief "focus here" --mode correctness
python3 external_critic.py path/to/draft.md --panel         # OR run the whole remembered panel; paid seats spend-gated
```

*(`setup.sh` remains a bash-only quick path for local Ollama; `critic_setup.py` is the cross-platform superset.)* `external_critic.py` logs the model + sampling params on every run (`critique.log`, next to the helper; `--no-log` to skip) so a review is auditable. (`seed` is logged for local Ollama where it's honored; cloud logs `na`.)

## Optional — a read-only status line for an integrating project

Wiring this skill into a larger project (one with its own `.claude/`)? You can surface critic status at session start **without the skill installing anything** — keep it read-only (no writes, no network at startup). The skill ships the tools (`--configure`, `--install`, `--panel`); the host project decides whether to advertise them. A `SessionStart` hook body:

```bash
if [ -f .critic/critic_panel.json ]; then       # set by `external_critic.py --configure --project`
  echo "External critic: project panel set — run \`external_critic.py <file> --panel\`."
else
  echo "External critic (optional): \`critic_setup.py --install\` sets it up (it asks first)."
fi
```

This is a *consumer* concern: **the skill itself registers no hooks.** A project `./.critic/` panel overrides the global one (no merge), so per-project critics stay isolated.

## Cloud routing — where the keys live

The skill is **not tied to any one vendor** — it's about *your* key. Store each provider's key **once**, under its own item, and the helper **finds it by itself** — `--configure`, `--panel`, and any run whose `CRITIC_BASE_URL` matches a known provider read the store directly (read-only; the key is never printed and never lands in a dotfile or your history). One provider key can serve several lineages (the google key serves Gemini *and* Gemma), so items are named **by provider**, `critic-api-key-<provider>`:

```bash
# store EACH provider's key once (each command PROMPTS — the key never touches your history):
#   macOS:   security add-generic-password -s critic-api-key-google -a "$USER" -w
#   Linux:   secret-tool store --label=critic-api-key-google service critic-api-key-google
#   Windows: [Environment]::SetEnvironmentVariable("CRITIC_API_KEY_GOOGLE",(Read-Host "key"),"User")

# Cloudflare additionally needs your account id (in the dashboard URL; NOT a secret):
#   export CLOUDFLARE_ACCOUNT_ID=<id>          # shell rc, or a line in the skill's .env

python3 external_critic.py --configure        # sees every provider with a stored key
python3 external_critic.py draft.md --panel   # each seat loads its own key; paid seats ask first
```

**Per-OS resolution** (`critic_setup.py --provider <x>` prints the exact commands for your machine):

- **macOS** — the Keychain, read via `security find-generic-password` (you may get a one-time "allow" prompt per item).
- **Linux** — libsecret (GNOME Keyring / KWallet), read via `secret-tool lookup`; install `libsecret-tools` if missing. Headless boxes without a keyring: fall back to env vars.
- **Windows** — a per-provider **user environment variable** `CRITIC_API_KEY_<PROVIDER>` (set via `Read-Host` above so it never enters PSReadLine history). Python's stdlib can't read Credential Manager, and this helper stays dependency-free — so on Windows the env var *is* the store.
- **Everywhere** — an explicit `CRITIC_API_KEY` (env or `.env`) always wins over the store; keyless local endpoints need nothing.

The optional **`critic-env <provider> [model]`** shell function (installed by `critic_setup.py --install`, printed by `--provider <x>`) is now just a *convenience* for one-off single-seat runs: it flips `CRITIC_BASE_URL`/`CRITIC_MODEL` per provider in one word. The panel never needs it.

**Several keys coexist** — one item each. The registry keeps every capable seat across providers, and `--configure` builds **one panel spanning all your distinct lineages** — that diversity *is* the decorrelation the panel is for.

Don't hard-code a model — `--discover` lists what the key serves, newest-first, so a new release auto-surfaces and you choose by score and free/paid (providers without a `/models` endpoint fall back to `STATIC_MODELS`). The helper omits request fields strict OpenAI-compat shims reject (e.g. `seed`) and surfaces the endpoint's own error text if a request is refused.

For a **published skill**, automate *detection and guidance*, not silent installation: when the user turns the reviewer on, run the preflight; if Ollama isn't ready, report the one command (`./setup.sh`) and the approximate download size, and leave installing/pulling to explicit consent. Never silently install software or pull multi-GB models on a user's machine.
