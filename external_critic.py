#!/usr/bin/env python3
"""
external_critic.py — get an INDEPENDENT critique from a local Ollama model (or a
hosted OpenAI-compatible endpoint), formatted to feed the Spatiotemporal Critique
synthesis step.

Why this exists: the framework's spatial critics, run by one model in one
context, only *approximate* independence. A different-lineage model gives
uncorrelated errors and an out-of-distribution check.

How to weight it: the value is INDEPENDENCE, not authority. A local open model
is usually weaker than Claude, so:
  - agreement with Claude  -> strong corroboration
  - disagreement           -> a 'contested' point to surface, not a verdict
Never let the external critique override better judgment. The discerning-solver
mandate applies: the synthesizer may reject it where it's wrong.

On intent: it may SURFACE objective-level doubt (alternative readings, severe
tests) for the user to adjudicate, but cannot unilaterally confirm meaning.

Usage:
    python3 external_critic.py ARTIFACT_FILE \
        [--brief "what to focus on"] \
        [--intent "the externalized intent spec"] \
        [--mode correctness|taste]
    # ARTIFACT_FILE of "-" reads from stdin.

Config (env / .env — a set, non-empty env var always wins):
    OLLAMA_HOST    default http://localhost:11434
    CRITIC_MODEL   default qwen3:8b  (a current, broadly-runnable, different-
                   lineage baseline; bump up for serious reviews)
                   - general, stronger:  qwen3:14b / qwen3:32b, or a current GLM
                     or DeepSeek tag (verify on ollama.com/library)
                   - code review:         a Qwen3-Coder or DeepSeek-Coder tag
                   Pick a lineage DIFFERENT from Claude to maximize independence,
                   and verify the exact tag on ollama.com/library — these move
                   monthly. For reproducible work, pin the tag per review and
                   record which model produced the critique.
    CRITIC_LOG     default: critique.log next to this script — per-run pin+log
                   (model, seed, params); --no-log to skip.
    .env           setup.sh writes its chosen model here (real env vars win).
    CRITIC_BASE_URL  set → OpenAI-compatible endpoint, base incl. the version path
                   (e.g. .../v1); a hosted, different-lineage model sent off-machine.
                   Empty = local Ollama (private, default).
    CRITIC_API_KEY   Bearer token for CRITIC_BASE_URL (keep in env, not .env).
"""
import argparse
import datetime
import json
import os
import sys
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load_dotenv(path):
    """Minimal .env reader (stdlib only): KEY=VALUE lines; # comments ignored.
    setup.sh writes its chosen model here so the helper uses the same one."""
    vals = {}
    try:
        with open(path, encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                vals[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return vals


_DOTENV = _load_dotenv(os.path.join(_HERE, ".env"))


def _cfg(key, default):
    # precedence: real environment > .env (setup's pick) > built-in fallback
    return os.environ.get(key) or _DOTENV.get(key) or default


HOST = _cfg("OLLAMA_HOST", "http://localhost:11434")
MODEL = _cfg("CRITIC_MODEL", "qwen3:8b")
LOG_PATH = _cfg("CRITIC_LOG", os.path.join(_HERE, "critique.log"))

# Fixed seed → a pinned tag yields a reproducible critique on the same model build.
OPTIONS = {"temperature": 0.4, "seed": 0}

# Cloud opt-in: set CRITIC_BASE_URL to an OpenAI-compatible endpoint (a hosted,
# different-lineage model) to send the critique off-machine. Empty = local Ollama
# (private; nothing leaves the box). CRITIC_API_KEY is sent as a Bearer token.
BASE_URL = _cfg("CRITIC_BASE_URL", "")
API_KEY = _cfg("CRITIC_API_KEY", "")
ENDPOINT = BASE_URL or HOST   # what actually served the critique (display + log)

SYSTEM = (
    "You are an independent reviewer with no stake in this work and no prior "
    "context. Be specific and honest; do not pad or hedge. Return exactly:\n"
    "1. PRESERVE — what is working and must not be lost (concrete).\n"
    "2. ISSUES — the highest-leverage problems, each as: "
    "[severity high/med/low] the problem — a concrete fix.\n"
    "For taste/creative work, replace ISSUES with GENERIC — the places it "
    "reads as generic or safe, each with a sharper alternative.\n"
    "End with one line: VERDICT — is this genuinely good as-is, or not, and why."
)


def build_prompt(artifact, brief, intent, mode):
    parts = []
    if intent:
        parts.append("INTENDED GOAL (what the author is trying to achieve):\n"
                     f"{intent}\n")
    if brief:
        parts.append(f"FOCUS:\n{brief}\n")
    parts.append(f"MODE: {mode}\n")
    parts.append(f"WORK TO REVIEW:\n{artifact}")
    return "\n".join(parts)


def call_model(system, prompt):
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    headers = {"Content-Type": "application/json"}
    if BASE_URL:  # OpenAI-compatible endpoint (cloud, or any local /v1 server)
        url = f"{BASE_URL.rstrip('/')}/chat/completions"
        body = {"model": MODEL, "messages": messages, "stream": False, **OPTIONS}
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"
        path = ("choices", 0, "message", "content")
    else:         # Ollama native (default; private, on localhost)
        url = f"{HOST}/api/chat"
        body = {"model": MODEL, "messages": messages, "stream": False, "options": OPTIONS}
        path = ("message", "content")
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())
    for k in path:
        data = data[k]
    return data


def log_run(artifact, mode, brief, intent):
    """Pin-and-log: record which model (and sampling params) produced which
    critique — the logged-trace discipline the Temporal axis and ledger use.
    Returns True if the record was written."""
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    rec = (f"{ts}\tmodel={MODEL}\tendpoint={ENDPOINT}\tmode={mode}"
           f"\ttemp={OPTIONS['temperature']}\tseed={OPTIONS['seed']}"
           f"\tartifact={artifact}\tbrief={brief!r}\tintent={intent!r}\n")
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(rec)
        return True
    except OSError as e:
        print(f"(warning: could not write {LOG_PATH}: {e})", file=sys.stderr)
        return False


def main():
    ap = argparse.ArgumentParser(
        description="Independent critique via local Ollama or an OpenAI-compatible endpoint.")
    ap.add_argument("artifact", help="path to the work under review, or '-' for stdin")
    ap.add_argument("--brief", default="", help="what the critic should focus on")
    ap.add_argument("--intent", default="", help="the externalized intent spec")
    ap.add_argument("--mode", default="correctness",
                    choices=["correctness", "taste"])
    ap.add_argument("--no-log", action="store_true",
                    help="don't record this run in the critique log")
    args = ap.parse_args()

    if args.artifact == "-":
        text = sys.stdin.read()
    else:
        with open(args.artifact, encoding="utf-8") as f:
            text = f.read()

    try:
        out = call_model(SYSTEM, build_prompt(text, args.brief, args.intent, args.mode))
    except Exception as e:  # noqa: BLE001 — surface any failure plainly
        if BASE_URL:
            sys.exit(f"external critic unavailable ({e}). Check CRITIC_BASE_URL "
                     f"({BASE_URL}), CRITIC_API_KEY, and the model name '{MODEL}'.")
        sys.exit(f"external critic unavailable ({e}). Is Ollama running? "
                 f"Try `ollama serve` and `ollama pull {MODEL}`.")

    where = f" @ {ENDPOINT}" if BASE_URL else ""
    print(f"=== EXTERNAL CRITIC ({MODEL}{where}) — independent viewpoint, weight by "
          f"agreement ===\n{out}")

    if not args.no_log and log_run(
            "<stdin>" if args.artifact == "-" else args.artifact,
            args.mode, args.brief, args.intent):
        print(f"(logged: {MODEL} -> {LOG_PATH})", file=sys.stderr)


if __name__ == "__main__":
    main()
