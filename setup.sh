#!/usr/bin/env bash
# setup.sh — preflight + guided setup for the external reviewer.
#   Local (default): ollama installed -> server -> spec-aware pick -> pull (consent) -> smoke.
#   Cloud (CRITIC_BASE_URL set): skip Ollama; check endpoint/key -> smoke.
# Safe by default: installs NOTHING unless --install, asks before any pull, writes its pick
# to .env so external_critic.py uses the same config. Secrets stay in your environment.

set -euo pipefail
cd "$(dirname "$0")"   # so relative paths (external_critic.py, .env) resolve

OLLAMA_HOST_DEFAULT="http://localhost:11434"
OLLAMA_HOST="${OLLAMA_HOST:-$OLLAMA_HOST_DEFAULT}"
CRITIC_BASE_URL="${CRITIC_BASE_URL:-}"      # set => cloud / OpenAI-compatible mode
CRITIC_MODEL_OVERRIDE="${CRITIC_MODEL:-}"   # non-empty => explicit pin
ENV_FILE=".env"
DO_INSTALL=0
[[ "${1:-}" == "--install" ]] && DO_INSTALL=1

# Ranked preference list — current, broadly-runnable, DIFFERENT-LINEAGE-from-Claude
# models, BEST FIRST. setup reuses the best of these you already have that fits your RAM;
# if none is installed it pulls PULL_DEFAULT (a light floor) with consent. Refresh by
# hand — tags + sizes move monthly (verify on ollama.com/library). CRITIC_SIZES are
# approx loaded GB, used to size-gate vs RAM and label recommendations.
# Order reflects a local benchmark (planted-bug code review): gpt-oss:20b found 4/5 in 35s
# fully on GPU — the best safe pick up to ~14 GB; the 27B is for bigger (>=~33 GB) machines.
# Code review: pin a code model explicitly, e.g. CRITIC_MODEL=qwen3-coder ./setup.sh
CRITIC_MODELS=( "gpt-oss:20b" "qwen3.6:27b-q4_K_M" "deepseek-r1:14b" )
CRITIC_SIZES=(  14            22                    9                )
PULL_DEFAULT="qwen3:8b"   # ~5 GB light floor, pulled only if nothing above is installed

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }
note() { printf '    %s\n' "$*"; }

# ── Cloud mode: a hosted endpoint is configured; skip Ollama entirely ────────────
if [[ -n "$CRITIC_BASE_URL" ]]; then
  say "cloud mode · CRITIC_BASE_URL=$CRITIC_BASE_URL"
  if [[ -n "$CRITIC_MODEL_OVERRIDE" ]]; then ok "model: $CRITIC_MODEL_OVERRIDE"
  else warn "no CRITIC_MODEL set — the helper needs the hosted model's name."; fi
  if [[ -n "${CRITIC_API_KEY:-}" ]]; then ok "CRITIC_API_KEY present"
  else warn "CRITIC_API_KEY not set — fine for keyless endpoints, else export it."; fi
  warn "privacy: cloud mode sends the artifact under review off your machine."
  note "cloud is fully env-driven (nothing written to .env, so a later plain run"
  note "stays local-private): keep CRITIC_BASE_URL, CRITIC_API_KEY and CRITIC_MODEL"
  note "exported in your shell for each cloud run."
  say "smoke test"
  if printf 'ok' | python3 external_critic.py - --brief "sanity check" --no-log >/dev/null 2>&1; then
    ok "round-trip works"
    say "ready · cloud reviewer at $CRITIC_BASE_URL"
  else
    echo "  smoke test failed — check CRITIC_BASE_URL / CRITIC_API_KEY / CRITIC_MODEL."; exit 1
  fi
  exit 0
fi

# ── Local mode (Ollama) ──────────────────────────────────────────────────────────
# 1 · ollama installed?
say "1/4 · checking ollama is installed"
if command -v ollama >/dev/null 2>&1; then
  ok "ollama found: $(command -v ollama)"
elif [[ "$DO_INSTALL" == 1 ]]; then
  case "$(uname -s)" in
    Darwin)
      if command -v brew >/dev/null 2>&1; then brew install ollama
      else echo "  Install from https://ollama.com/download, then re-run."; exit 1; fi ;;
    Linux)
      echo "  This will run: curl -fsSL https://ollama.com/install.sh | sh"
      read -rp "  Proceed? [y/N] " a || a=""
      [[ "$a" == "y" || "$a" == "Y" ]] && curl -fsSL https://ollama.com/install.sh | sh || exit 1 ;;
    *) echo "  Install manually from https://ollama.com/download"; exit 1 ;;
  esac
else
  warn "ollama not installed."
  echo "  Install it (then re-run), or re-run this script with --install:"
  echo "    macOS:  brew install ollama   (or https://ollama.com/download)"
  echo "    Linux:  curl -fsSL https://ollama.com/install.sh | sh"
  echo "  Or go cloud: set CRITIC_BASE_URL (+ CRITIC_API_KEY) and re-run."
  exit 1
fi

# 2 · server reachable? (start if not)
say "2/4 · checking the server at $OLLAMA_HOST"
if curl -fsS "$OLLAMA_HOST/api/version" >/dev/null 2>&1; then
  ok "server reachable"
else
  warn "server not reachable — starting 'ollama serve' in the background"
  ollama serve >/tmp/ollama-setup.log 2>&1 &
  for _ in $(seq 1 20); do
    curl -fsS "$OLLAMA_HOST/api/version" >/dev/null 2>&1 && break
    sleep 0.5
  done
  curl -fsS "$OLLAMA_HOST/api/version" >/dev/null 2>&1 \
    && ok "server up" \
    || { echo "  could not start the server; see /tmp/ollama-setup.log"; exit 1; }
fi

# detect total RAM (GB) for the spec-aware recommendation (0 = unknown)
ram_gb() {
  local b
  case "$(uname -s)" in
    Darwin) b=$(sysctl -n hw.memsize 2>/dev/null || echo 0); echo $(( b / 1073741824 )) ;;
    Linux)  awk '/MemTotal/{printf "%d", $2/1048576; exit}' /proc/meminfo 2>/dev/null || echo 0 ;;
    *)      echo 0 ;;
  esac
}
RAM=$(ram_gb)
# Rough unified-memory / CPU-inference budget (we deliberately skip fragile VRAM
# probing): a model is SAFE to auto-pick under ~60% of RAM, runs (tight) under ~2/3.
# (Empirically here: gpt-oss:20b at 14GB/58% stayed 100% GPU; the 27B at ~22GB/71% spilled.)
COMFORT=$(( RAM * 60 / 100 ))
TIGHT=$(( RAM * 2 / 3 ))

installed_raw="$(ollama list 2>/dev/null | awk 'NR>1 {print $1}' || true)"
is_installed() { grep -Fqx "$1" <<<"$installed_raw"; }
within() {  # within SIZE BUDGET -> 0 if size fits the budget (or RAM unknown)
  [[ "$RAM" -eq 0 ]] && return 0
  [[ "$1" -le "$2" ]] && return 0
  return 1
}
fit_label() {
  if   [[ "$RAM" -eq 0 ]];        then echo "size ~${1}GB"
  elif [[ "$1" -le "$COMFORT" ]]; then echo "comfortable"
  elif [[ "$1" -le "$TIGHT" ]];   then echo "runs, tight on ${RAM}GB"
  else echo "too big for ${RAM}GB — consider cloud"; fi
}

# 3 · spec-aware recommendation, then selection
if [[ "$RAM" -gt 0 ]]; then say "3/4 · model — this machine has ${RAM}GB RAM"
else say "3/4 · model (RAM unknown — showing sizes only)"; fi
for i in "${!CRITIC_MODELS[@]}"; do
  name="${CRITIC_MODELS[$i]}"; size="${CRITIC_SIZES[$i]}"
  if is_installed "$name"; then tag="installed"; else tag="pull ~${size}GB"; fi
  note "$((i+1)). $name — $tag; $(fit_label "$size")"
done
note "cloud: set CRITIC_BASE_URL (+ CRITIC_API_KEY) for a hosted different-lineage"
note "model instead — stronger than local, but sends the draft off your machine."

# select: explicit pin > best COMFORTABLE installed > best installed that still
#         runs (tight) > pull the light floor.  We never auto-pick a model too big
#         for RAM (it would spill to CPU and crawl) — pin it explicitly
#         (CRITIC_MODEL=...) or go cloud for something bigger than your machine.
CHOSEN=""
if [[ -n "$CRITIC_MODEL_OVERRIDE" ]]; then
  CHOSEN="$CRITIC_MODEL_OVERRIDE"
  ok "using pinned CRITIC_MODEL=$CHOSEN"
else
  for budget in "$COMFORT" "$TIGHT"; do
    for i in "${!CRITIC_MODELS[@]}"; do
      if is_installed "${CRITIC_MODELS[$i]}" && within "${CRITIC_SIZES[$i]}" "$budget"; then
        CHOSEN="${CRITIC_MODELS[$i]}"; break 2
      fi
    done
  done
  if [[ -n "$CHOSEN" ]]; then ok "reusing installed model that fits: $CHOSEN"
  else CHOSEN="$PULL_DEFAULT"; ok "no installed model fits RAM — pull default: $CHOSEN"; fi
fi

# ensure present (pull only with explicit consent — pulls can be several GB)
if is_installed "$CHOSEN"; then
  ok "model present"
else
  warn "model '$CHOSEN' is not installed — pulling it can be several GB."
  if [[ -t 0 ]]; then
    read -rp "  Pull '$CHOSEN' now? [y/N] " a || a=""
    [[ "$a" == "y" || "$a" == "Y" ]] \
      || { echo "  declined — set CRITIC_MODEL to an installed tag and re-run."; exit 1; }
  elif [[ "${CRITIC_PULL_OK:-0}" != "1" ]]; then
    echo "  non-interactive: refusing to pull without consent."
    echo "  re-run with CRITIC_PULL_OK=1 to allow, or pre-pull: ollama pull $CHOSEN"
    exit 1
  fi
  ollama pull "$CHOSEN"
fi

# pin the choice so external_critic.py uses the same model (real env vars still win).
# .env is regenerated every run — to keep a custom pin, pass CRITIC_MODEL=... or set it
# in your environment; the helper reads real env vars before .env.
{
  echo "# Regenerated by setup.sh on each run — edits here are overwritten."
  echo "# To pin a custom model: CRITIC_MODEL=<tag> ./setup.sh"
  echo "CRITIC_MODEL=$CHOSEN"
  if [[ "$OLLAMA_HOST" != "$OLLAMA_HOST_DEFAULT" ]]; then echo "OLLAMA_HOST=$OLLAMA_HOST"; fi
} > "$ENV_FILE"
ok "pinned to $ENV_FILE (CRITIC_MODEL=$CHOSEN)"

# 4 · smoke test (full round-trip through the helper; this run is not logged)
say "4/4 · smoke test"
if printf 'ok' | python3 external_critic.py - --brief "one-line sanity check" --no-log >/dev/null 2>&1; then
  ok "round-trip works"
else
  echo "  smoke test failed — try: python3 external_critic.py - --brief test"; exit 1
fi

say "ready · external reviewer configured with: $CHOSEN"
echo "every real run is appended to critique.log next to the helper (pin+log;"
echo "model, seed and params recorded — auditable, reproducible on the same build)."
echo "test it on real work:"
echo "  python3 external_critic.py YOUR_FILE --brief 'focus here' --mode correctness"
