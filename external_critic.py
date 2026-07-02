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
        [--mode correctness|taste] \
        [--depth brief|full]
    # ARTIFACT_FILE of "-" reads from stdin; --depth full adds a rationale per finding.

    python3 external_critic.py --probe [--cost free|paid]
    # CAPABILITY PROBE (availability != capability): grade the configured seat on a tiny
    # MULTI-FLAW artifact; SCORE = how many planted flaws it NAMES (PASS = score >= 1,
    # FAIL = a null seat that summarizes, UNAVAILABLE = it didn't answer). The score is a
    # quantitative proxy that ranks the panel. Deterministic, non-LLM grader.

    python3 external_critic.py --configure [--auto] [--project] [--choose "m1,m2"]
    # PICK your panel: configured providers -> grouped-by-lineage table -> pick 1-3 (or --auto
    # for the score-ranked, free-first suggestion) -> REMEMBER it (critic_panel.json). Re-run to
    # keep/update; flags new models. Paid listed UNPROBED. --project saves to ./.critic/.

    python3 external_critic.py ARTIFACT_FILE --panel [--yes]
    # RUN the remembered panel: each chosen seat critiques ARTIFACT_FILE; every view prints as
    # a CONTESTED input for synthesis. Paid seats are spend-gated (--yes to allow them).

Config (env / .env — a set, non-empty env var always wins):
    OLLAMA_HOST    default http://localhost:11434
    CRITIC_MODEL   default qwen3:8b  (a current, broadly-runnable, different-
                   lineage baseline; bump up for serious reviews)
                   - general, stronger:  gemma4:12b / qwen3:14b / qwen3:32b, or a
                     current GLM or DeepSeek tag (verify on ollama.com/library)
                   - code review:         a Qwen3-Coder or DeepSeek-Coder tag
                   Pick a lineage DIFFERENT from Claude to maximize independence,
                   and verify the exact tag on ollama.com/library — these move
                   monthly. For reproducible work, pin the tag per review and
                   record which model produced the critique.
    CRITIC_LOG     default: critique.log next to this script — per-run pin+log
                   (model, seed, params); --no-log to skip.
    CRITIC_REGISTRY default: critic_registry.tsv next to this script — the
                   capability-probe log {date · model · lineage · probe · cost}.
    .env           setup.sh writes its chosen model here (real env vars win).
    CRITIC_BASE_URL  set → OpenAI-compatible endpoint, base incl. the version path
                   (e.g. .../v1); a hosted, different-lineage model sent off-machine.
                   Empty = local Ollama (private, default).
    CRITIC_API_KEY   Bearer token for CRITIC_BASE_URL. Resolution: env / .env first;
                   else, when CRITIC_BASE_URL matches a known provider, the key is
                   read from the OS secret store (item critic-api-key-<provider> —
                   macOS Keychain / Linux secret-tool / Windows per-provider env var
                   CRITIC_API_KEY_<PROVIDER>). Keep keys out of .env.
    CLOUDFLARE_ACCOUNT_ID  fills Cloudflare's per-account base URL (env or .env;
                   the account id is not a secret).
"""
import argparse
import datetime
import json
import os
import platform
import re
import subprocess
import sys
import urllib.error
import urllib.request

try:
    from critic_providers import PROVIDERS, STATIC_MODELS, resolve_base
except ImportError:                          # --configure needs them; probe/discover don't
    PROVIDERS, STATIC_MODELS = {}, {}

    def resolve_base(base):
        return base

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

# Cloudflare's base URL is per-account; .env may carry the id (it is not a secret).
# Bridged into the environment so resolve_base sees it; a real env var wins.
if not os.environ.get("CLOUDFLARE_ACCOUNT_ID") and _DOTENV.get("CLOUDFLARE_ACCOUNT_ID"):
    os.environ["CLOUDFLARE_ACCOUNT_ID"] = _DOTENV["CLOUDFLARE_ACCOUNT_ID"]


def _cfg(key, default):
    # precedence: real environment > .env (setup's pick) > built-in fallback
    return os.environ.get(key) or _DOTENV.get(key) or default


HOST = _cfg("OLLAMA_HOST", "http://localhost:11434")
MODEL = _cfg("CRITIC_MODEL", "qwen3:8b")
LOG_PATH = _cfg("CRITIC_LOG", os.path.join(_HERE, "critique.log"))

# Ollama native: seed honored under "options" → a pinned tag gives a reproducible critique.
OPTIONS = {"temperature": 0.4, "seed": 0}
# OpenAI-compat shims reject UNKNOWN fields (Gemini 400s on `seed`), so the cloud path
# sends only the universal knob; cloud reproducibility is pin+log, not a bitwise seed.
OPENAI_OPTIONS = {"temperature": OPTIONS["temperature"]}

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

# --depth full: opt-in size dial (mirrors Quick/Standard sizing) — rationale on the
# same contract, structured, not padding.
DEPTH_FULL = (
    "\nDEPTH=full: for each ISSUE/GENERIC item, add a 'why:' line — one sentence "
    "on why it matters or how you'd know it's real. Just before VERDICT, add a "
    "short REASONING block (2-4 sentences) weighing the main trade-off. Keep it "
    "tight — rationale, not padding."
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


def call_model(system, prompt, model=None, base_url=None, api_key=None):
    # Per-seat overrides (--panel runs several seats); each falls back to the module global.
    model = model or MODEL
    base_url = BASE_URL if base_url is None else base_url
    api_key = API_KEY if api_key is None else api_key
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    headers = {"Content-Type": "application/json"}
    if base_url:  # OpenAI-compatible endpoint (cloud, or any local /v1 server)
        url = f"{base_url.rstrip('/')}/chat/completions"
        body = {"model": model, "messages": messages, "stream": False, **OPENAI_OPTIONS}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        path = ("choices", 0, "message", "content")
    else:         # Ollama native (default; private, on localhost)
        url = f"{HOST}/api/chat"
        body = {"model": model, "messages": messages, "stream": False, "options": OPTIONS}
        path = ("message", "content")
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:  # surface the endpoint's reason (e.g. a rejected field)
        detail = e.read().decode("utf-8", "replace").strip()[:500]
        raise RuntimeError(f"HTTP {e.code} from {url} — {detail}") from None
    for k in path:
        data = data[k]
    return data


def log_run(artifact, mode, depth, brief, intent, model=None, endpoint=None, base_url=None):
    """Pin-and-log: record which model (and sampling params) produced which
    critique — the logged-trace discipline the Temporal axis and ledger use.
    depth is logged too: it changes the prompt, so it's part of reproducibility.
    model/endpoint/base_url override the globals so --panel logs each seat.
    Returns True if the record was written."""
    model, endpoint = model or MODEL, endpoint or ENDPOINT
    cloud = BASE_URL if base_url is None else base_url
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    seed = "na" if cloud else OPTIONS["seed"]  # seed isn't sent on the cloud path
    rec = (f"{ts}\tmodel={model}\tendpoint={endpoint}\tmode={mode}\tdepth={depth}"
           f"\ttemp={OPTIONS['temperature']}\tseed={seed}"
           f"\tartifact={artifact}\tbrief={brief!r}\tintent={intent!r}\n")
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(rec)
        return True
    except OSError as e:
        print(f"(warning: could not write {LOG_PATH}: {e})", file=sys.stderr)
        return False


# --- Capability detection: availability != capability ------------------------
# A reachable seat is not a capable one. Real seats (gpt-oss, deepseek-r1) have
# been reachable yet returned NULL critiques — regenerating or summarizing the
# artifact instead of finding its flaw ("independence-theater": a seat that adds
# no real check still looks like a second opinion). The probe applies the
# planted-defect discipline to the critic seat ITSELF: feed a tiny artifact with
# ONE known flaw and check that the seat NAMES it. The grader is a deterministic,
# non-LLM string check — a DIFFERENT SUBSTRATE from the seat under test — so
# auto-excluding a null seat is a legitimate gate (gate on a different substrate;
# only advise on a same-lineage judgment). A PASS certifies the seat genuinely
# critiques; it NEVER grants authority over whether the Intent is right (that
# residual stays the owner's).

REGISTRY_PATH = _cfg("CRITIC_REGISTRY", os.path.join(_HERE, "critic_registry.tsv"))
REPROBE_DAYS = 30  # model tags mutate; a PASS older than this is stale -> re-probe

# A tiny PROSE artifact with TWO independent, blatant flaws — matched to the real use
# case (these seats review DOCS). The capability SCORE = how many the seat NAMES (0-2):
# a quantitative proxy that RANKS seats for the panel (a misrank only reorders
# the panel; the PASS gate stays binary, PASS = score >= 1). Each flaw's diagnosis words
# are engineered ABSENT from the artifact (so an echo/summary scores 0) and use DISTINCT
# vocab (compatibility vs testing) so the two are separately attributable.
PROBE_ARTIFACT = (
    "Release note: this update is fully backward-compatible — no existing call needs "
    "to change. It also removes the get_user() endpoint, so every caller must migrate "
    "to fetch_user().\n"
    "Early benchmarks show it cuts memory use by 250%.\n"
)
PROBE_BRIEF = "Review this for correctness, soundness, and internal consistency."
# The capability SCORE counts flaws NAMED — but diagnosis vocabulary is OPEN-ended (a seat
# may call the bad number "negative", "unrealistic", "impossible", or "over 100%"), so pure
# per-flaw token lists keep false-missing capable seats (observed). Instead, a flaw is NAMED
# when SOME SENTENCE pairs that flaw's SUBJECT ANCHOR with ANY critical word (below). The
# anchor scopes the critical word to the right flaw (no cross-contamination between flaws),
# and a summary that merely restates the subject — with no critical word in that sentence —
# scores 0. Two flaws of DIFFERENT type: flaw A is blatant (gates PASS); flaw B is sharper
# (a >100% reduction is impossible) so it discriminates a strong seat (2) from a shallow one (1).
PROBE_FLAWS = (
    ("backward-compat contradiction", ("backward", "compatib", "get_user", "fetch_user", "migrate")),
    ("impossible >100% reduction",    ("250", "memory", "footprint")),
)
# A critical word marks a sentence as a CRITIQUE (not a restatement). Restricted to
# epistemic/logical FAULT words — generic operational verbs ("cannot", "error", "invalid")
# are excluded because a plain summary uses them ("removes get_user, so you cannot call it"),
# which would false-PASS a null seat (Gemini's finding). The subject anchor keeps credit specific.
PROBE_CRITICAL = ("contradict", "inconsisten", "conflict", "breaking", "breaks", "regression",
                  "incompatible", "impossible", "unrealistic", "implausible", "nonsens",
                  "absurd", "negative", "incorrect", "wrong", "false", "more than 100",
                  "over 100", "exceed", "makes no sense", "no sense", "not possible", "mismatch")
PROBE_TOKENS = PROBE_CRITICAL  # grade_probe default (the faithful --expect path passes its own)
PROBE_MIN_LEN = 25  # below this the seat returned nothing usable (a null answer)


def _strip_reasoning(s):
    """Grade the seat's ANSWER, not its scratchpad: drop a <think>…</think> block
    (reasoning models like deepseek-r1 emit one; a contradiction noticed only in
    private reasoning but absent from the answer still reaches synthesis as null)."""
    low = s.lower()
    i, j = low.find("<think>"), low.find("</think>")
    if i != -1 and j != -1 and j > i:
        return s[:i] + s[j + len("</think>"):]
    return s


def infer_lineage(model, base_url):
    """Best-effort model family from the id / endpoint. The point is: != Claude."""
    m, u = (model or "").lower(), (base_url or "").lower()
    table = [
        ("gemini", ("gemini", "gemma", "generativelanguage", "googleapis")),
        ("gpt", ("gpt-", "openai.com", "o1-", "o3-", "o4-")),
        ("deepseek", ("deepseek",)),
        ("glm", ("glm", "z.ai", "zhipu", "bigmodel")),
        ("mistral", ("mistral", "mixtral", "magistral")),
        ("qwen", ("qwen",)),
        ("kimi", ("kimi", "moonshot")),
        ("sonar", ("sonar", "perplexity")),
        ("llama", ("llama",)),
        ("claude", ("claude", "anthropic")),
    ]
    for name, needles in table:
        if any(n in m or n in u for n in needles):
            return name
    return "unknown"


def infer_cost(base_url, api_key, override):
    if override:
        return override
    if not base_url:
        return "free"                          # local Ollama, on this box
    return "paid" if api_key else "free"        # keyless local /v1 server = free


def grade_probe(output, tokens=PROBE_TOKENS, what="the contradiction"):
    """Deterministic, non-LLM grade. PASS iff the seat NAMED the planted flaw.
    A positive token match WINS over the length floor, so a terse-but-correct seat
    ("Contradiction: removes an endpoint.") is not false-failed. Matched lowercased
    but space-preserved — no substring collisions."""
    answer = _strip_reasoning(output or "").lower()
    hit = next((t for t in tokens if t in answer), None)
    if hit:
        return True, f"named {what} (matched '{hit.strip()}')"
    if len(answer.strip()) < PROBE_MIN_LEN:
        return False, "null / too-short (returned nothing usable)"
    return False, f"did NOT name {what} (regenerated/summarized)"


def score_probe(output):
    """Deterministic, non-LLM capability SCORE = number of the PROBE_FLAWS the seat
    NAMES (0..N). A flaw is NAMED when some SENTENCE pairs its subject anchor with any
    critical word — tolerant of open diagnosis vocabulary, yet a restating summary (no
    critical word) scores 0. Grades the seat's ANSWER (a <think> block stripped). The
    gate is binary (PASS = score >= 1); the score RANKS the panel."""
    answer = _strip_reasoning(output or "")
    if len(answer.strip()) < PROBE_MIN_LEN:
        return 0, []
    sents = [s.lower() for s in re.split(r"[.\n;!?]+", answer) if s.strip()]
    # Windows = each sentence AND each adjacent pair: a critique often states the premise
    # in one sentence and the fault in the next ("...a 250% cut. That is impossible.") —
    # the pair window catches that without a paragraph's cross-flaw contamination.
    windows = sents + [sents[i] + " " + sents[i + 1] for i in range(len(sents) - 1)]
    named = [label for label, anchors in PROBE_FLAWS
             if any(any(a in w for a in anchors) and any(c in w for c in PROBE_CRITICAL)
                    for w in windows)]
    return len(named), named


def _int(s):
    try:
        return int(s)
    except (TypeError, ValueError):
        return 0


def _registry_records():
    recs = []
    try:
        with open(REGISTRY_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line or line.startswith("#"):
                    continue
                kv = dict(p.split("=", 1) for p in line.split("\t") if "=" in p)
                if kv:
                    recs.append(kv)
    except FileNotFoundError:
        pass
    return recs


def latest_per_model(recs):
    """Newest record wins per model (append-only file; a re-probe supersedes)."""
    out = {}
    for r in recs:                              # chronological; later overwrites
        if "model" in r:
            out[r["model"]] = r
    return out


def register(model, lineage, endpoint, result, cost, score, note):
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    rec = (f"date={ts}\tmodel={model}\tlineage={lineage}\tendpoint={endpoint}"
           f"\tprobe={result}\tscore={score}\tcost={cost}\tnote={note}\n")
    fresh = not os.path.exists(REGISTRY_PATH)
    try:
        with open(REGISTRY_PATH, "a", encoding="utf-8") as f:
            if fresh:
                f.write("# external-critic capability registry — planted-defect probe results.\n")
                f.write("# PASS = seat NAMED a known flaw (genuine critique); FAIL/UNAVAILABLE = null seat.\n")
            f.write(rec)
        return True
    except OSError as e:
        print(f"(warning: could not write {REGISTRY_PATH}: {e})", file=sys.stderr)
        return False


def _stale(date_str):
    try:
        d = datetime.datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        return False
    return (datetime.datetime.now() - d).days > REPROBE_DAYS


def do_probe(cost_override, artifact_path="", expect=""):
    """Stage 1+2+3: availability + capability in ONE cheap call, then register.

    Floor probe (default): the built-in tiny contradiction — excludes seats that
    are unreachable, return a stale-id error, or universally summarize/regenerate.
    Faithful probe (--probe FILE --expect "tok,..."): plant ONE known flaw in a
    slice of your REAL artifact and name what a genuine critic must say. This is the
    rung that catches ARTIFACT-SCALE degradation a tiny probe misses (a seat can pass
    the floor yet null on a large/abstract doc — observed: gpt-oss flags a one-line
    contradiction but summarized the governance bundle)."""
    lineage = infer_lineage(MODEL, BASE_URL)
    cost = infer_cost(BASE_URL, API_KEY, cost_override)
    faithful = bool(artifact_path)
    if faithful:
        try:
            art = sys.stdin.read() if artifact_path == "-" else \
                open(artifact_path, encoding="utf-8").read()
        except OSError as e:
            sys.exit(f"cannot read probe artifact {artifact_path}: {e}")
        # lowercase but PRESERVE spaces — grade_probe matches a space-preserved
        # answer, so a multi-word --expect ("race condition") must keep its space.
        toks = tuple(t.strip().lower() for t in expect.split(",") if t.strip())
        if not toks:
            sys.exit('--probe FILE needs --expect "tok1,tok2": the word(s) a genuine '
                     "critic must say when it finds the flaw you planted in FILE.")
        kind, total = f"faithful probe on {os.path.basename(artifact_path)}", 1
    else:
        art, kind, total = PROBE_ARTIFACT, "floor probe", len(PROBE_FLAWS)
    print(f"probing: model={MODEL}  lineage={lineage}  endpoint={ENDPOINT}  cost={cost}  [{kind}]")
    if lineage in ("claude", "anthropic"):
        print("WARNING: this seat shares the builder's lineage — a PASS gives no "
              "independence (same blind spot). Pick a different family.", file=sys.stderr)
    try:
        out = call_model(SYSTEM, build_prompt(art, PROBE_BRIEF, "", "correctness"))
    except Exception as e:  # noqa: BLE001 — any failure means the seat is unavailable
        register(MODEL, lineage, ENDPOINT, "UNAVAILABLE", cost, "na",
                 str(e).splitlines()[0][:120])
        print(f"UNAVAILABLE — {e}")
        print(f"(recorded UNAVAILABLE in {REGISTRY_PATH})", file=sys.stderr)
        return 2
    if faithful:                                    # binary: did it find the planted flaw?
        passed, signal = grade_probe(out, toks, "the planted flaw")
        score = 1 if passed else 0
    else:                                           # quantitative: how many flaws named?
        score, named = score_probe(out)
        passed = score >= 1
        signal = (f"named {score}/{total}: {', '.join(named)}" if named
                  else "named 0 flaws (regenerated/summarized)")
    result = "PASS" if passed else "FAIL"
    register(MODEL, lineage, ENDPOINT, result, cost, score, f"{kind}: {signal}")
    print(f"\n--- probe response (truncated) ---\n{out.strip()[:600]}\n----------------------------------")
    print(f"{result} (score {score}/{total}): {signal}")
    if not passed:
        print("  -> null seat: exclude it. A reachable model that won't name an obvious "
              "flaw adds no real check (independence-theater).")
    print(f"(recorded {result} score {score}/{total} in {REGISTRY_PATH})", file=sys.stderr)
    return 0 if passed else 1


def _suggest_panel(rows, top=3):
    """Auto-rank candidate rows -> the best seat per DISTINCT lineage (independence =
    diversity), by score then free-first, capped at `top`. This is the suggested default
    --configure offers (Enter / --auto). rows are [lineage, model, endpoint, cost, score]."""
    def key(r):
        return (_int(r[4]), r[3] == "free")
    best = {}
    for r in rows:
        if r[0] not in best or key(r) > key(best[r[0]]):
            best[r[0]] = r
    return sorted(best.values(), key=key, reverse=True)[:top]


# --- Model discovery: don't hard-code a model — list what the KEY can serve --------
# A given key exposes many models; the right one changes monthly. `--discover` queries
# the endpoint's model list, drops non-chat ids, sorts newest-first (so a newer release
# auto-surfaces), and annotates each with free|paid + its capability score (if probed).
# No price API exists, so cost is the free/paid TIER, not dollars; you pick which paid
# seats to probe + use (you pay per call); `--configure` lists paid UNPROBED and `--panel` asks first.
# Drop clearly-non-chat ids ONLY — by MODALITY, never by size. NOT "vision" (modern chat
# models are multimodal — gpt-4-vision, llava), NOT "gemma" (a capable open chat model), and
# NOT "nano" (a SIZE tier — gpt-5-nano / gpt-4.1-nano are real chat seats; nano-banana is
# already caught by "banana"). Excluding any of these would hide valid seats.
_NONCHAT = ("embed", "imagen", "image", "dall-e", "tts", "audio", "whisper", "banana", "rerank",
            "moderation", "guard", "robotic", "computer-use", "aqa", "-live", "diffusion",
            "veo", "speech", "transcrib", "lyria", "music")


def _suitable(model_id):
    m = model_id.lower()
    return bool(m) and not any(b in m for b in _NONCHAT)


def _strip_dates(s):
    """Drop date suffixes so they're not mistaken for versions (a model id like
    '…-preview-12-2025' must not parse as v12, out-ranking gemini-3.5)."""
    s = re.sub(r"[-_]\d{1,2}[-_]\d{4}\b", "", s)   # -MM-YYYY
    s = re.sub(r"[-_]\d{6,8}\b", "", s)            # -YYYYMM(DD)
    return re.sub(r"[-_]\d{4}\b", "", s)           # -YYYY


def _version(model_id):
    """Sort key: (major, minor). Handles 'x.y' and single-int 'gemini-3-pro'; date
    suffixes are stripped first; bare aliases ('*-latest') -> (0,0), sorted last."""
    s = _strip_dates(model_id)
    mt = re.search(r"(\d+)\.(\d+)", s)
    if mt:
        return (int(mt.group(1)), int(mt.group(2)))
    ms = re.search(r"[-_](\d+)(?:[-_]|$)", s)
    if ms:
        return (int(ms.group(1)), 0)
    mf = re.search(r"\d+", s)              # last resort: first digit (gpt-4o -> 4, deepseek-r1 -> 1)
    return (int(mf.group(0)), 0) if mf else (0, 0)


def discover_models():
    """Model ids the configured key/endpoint can serve. OpenAI-compat: GET /models;
    local Ollama: GET /api/tags."""
    if BASE_URL:
        url = f"{BASE_URL.rstrip('/')}/models"
        headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
        req = urllib.request.Request(url, headers=headers)
        data = json.loads(urllib.request.urlopen(req, timeout=20).read())
        return [m.get("id", "") for m in data.get("data", [])]
    url = f"{HOST}/api/tags"
    data = json.loads(urllib.request.urlopen(url, timeout=20).read())
    return [m.get("name", "") for m in data.get("models", [])]


def do_discover():
    """List suitable models for this key, newest-first, with cost tier + probe score."""
    cost = infer_cost(BASE_URL, API_KEY, "")
    try:
        ids = discover_models()
    except Exception as e:  # noqa: BLE001
        if BASE_URL:
            sys.exit(f"discover failed ({e}). Check CRITIC_BASE_URL ({BASE_URL}) and CRITIC_API_KEY.")
        sys.exit(f"discover failed ({e}). Is Ollama running? Try `ollama serve`.")
    chat = sorted({i for i in ids if _suitable(i)}, key=lambda i: (_version(i), i), reverse=True)
    if not chat:
        print(f"no suitable chat models found at {ENDPOINT} ({len(ids)} total returned).")
        return 1
    scored = latest_per_model(_registry_records())
    print(f"DISCOVERED {len(chat)} suitable chat models at {ENDPOINT}  (newest-first · cost={cost}):")
    for i in chat:
        name = i.replace("models/", "")
        rec = scored.get(name) or scored.get(i)
        if rec and rec.get("probe") == "PASS":
            mark = f"score {rec.get('score', '?')}"
        elif rec and rec.get("probe") in ("FAIL", "UNAVAILABLE"):
            mark = rec["probe"].lower()
        else:
            mark = "unprobed"
        v = _version(i)
        vtag = f"v{v[0]}.{v[1]}" if v != (0, 0) else "—"
        print(f"  {name:44} {vtag:6} {cost:4}  {mark}")
    top = chat[0].replace("models/", "")
    print(f"\nlatest suitable -> {top}")
    print(f"  certify it:  CRITIC_MODEL={top} python3 {os.path.basename(__file__)} --probe")
    print(f"  then pick:   python3 {os.path.basename(__file__)} --configure")
    if cost == "paid":
        print("  PAID endpoint: you pay per call — probe + use only the models you choose; "
              "`--configure` lists paid UNPROBED and `--panel` asks before spending.")
    return 0


# --- Remembered panel: the user's chosen 1-3 critics (single source of truth) ------
# Resolution: a project-local ./.critic/critic_panel.json OVERRIDES the global one
# (next to the registry) — no merge. --panel reads it; --configure writes it; the
# registry only supplies live scores. The project file is created ONLY by an explicit
# `--configure --project`; NOTHING writes it at startup.
PANEL_GLOBAL = _cfg("CRITIC_PANEL", os.path.join(_HERE, "critic_panel.json"))
PANEL_PROJECT = os.path.join(".critic", "critic_panel.json")
REFRESH_DAYS = 7   # a panel older than this is flagged "re-check for new models" (date-compare only)


def _panel_path_read():
    return PANEL_PROJECT if os.path.exists(PANEL_PROJECT) else PANEL_GLOBAL


def read_panel():
    try:
        with open(_panel_path_read(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def write_panel(selected, seen, project):
    path = PANEL_PROJECT if project else PANEL_GLOBAL
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {"selected": selected,
            "checked": datetime.datetime.now().isoformat(timespec="seconds"),
            "seen": sorted(set(seen))}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return path
    except OSError as e:
        sys.exit(f"could not write {path}: {e}")


def _panel_age_days(panel):
    try:
        return (datetime.datetime.now() - datetime.datetime.fromisoformat(panel.get("checked", ""))).days
    except (ValueError, TypeError):
        return 999


def _discover_at(base, key):
    req = urllib.request.Request(f"{base.rstrip('/')}/models",
                                 headers={"Authorization": f"Bearer {key}"} if key else {})
    data = json.loads(urllib.request.urlopen(req, timeout=20).read())
    return [m.get("id", "") for m in data.get("data", [])]


def _provider_key(provider):
    """Load a provider's stored key per-OS (read-only; never printed). None if absent."""
    item = f"critic-api-key-{provider}"
    try:
        if platform.system() == "Darwin":
            r = subprocess.run(["security", "find-generic-password", "-s", item, "-w"],
                               capture_output=True, text=True, timeout=5)
            return r.stdout.strip() or None
        if platform.system() == "Linux":
            r = subprocess.run(["secret-tool", "lookup", "service", item],
                               capture_output=True, text=True, timeout=5)
            return (r.stdout.strip() or None) if r.returncode == 0 else None
        if platform.system() == "Windows":
            return os.environ.get("CRITIC_API_KEY_" + provider.upper().replace("-", "_")) or None
    except Exception:  # noqa: BLE001 — best effort; missing key is normal
        return None
    return None


def _key_for(prov, base):
    """A provider's key: the OS secret store first, else the env CRITIC_API_KEY when `base`
    is the ACTIVE provider (a live `critic-env`/export) — so a panel just works with the
    key you already loaded. '' if none is reachable."""
    key = (_provider_key(prov) if prov else "") or ""
    if not key and API_KEY and base and base.rstrip("/") == (BASE_URL or "").rstrip("/"):
        key = API_KEY
    return key


def _candidate_rows():
    """Returns (table, seen, catalog). `table` = a BOUNDED grouped-by-lineage list for
    browsing — [lineage, model, endpoint, cost, score]; `catalog` = {model: row} for EVERY
    reachable seat (registry PASS + full free /models discovery per keyed provider) so
    `--choose` can name any servable model, not just a displayed one. Never probes (no paid
    call). Lineage is lower-cased so registry and discovery rows group as one lineage."""
    scored = latest_per_model(_registry_records())
    seen, table, listed, catalog = set(), [], set(), {}
    for r in scored.values():
        seen.add(r["model"])
        if r.get("probe") == "PASS" and r.get("lineage") not in ("claude", "anthropic"):
            row = [(r.get("lineage") or "?").lower(), r["model"], r.get("endpoint", ""),
                   r.get("cost", "?"), str(r.get("score", "?"))]
            table.append(row); listed.add(r["model"]); catalog[r["model"]] = row
    for prov, (lineage, base) in PROVIDERS.items():
        base = resolve_base(base)                      # None = {account} unfilled -> skip
        if not base:
            continue
        key = _key_for(prov, base)
        if not key:
            continue
        try:
            ids = _discover_at(base, key)              # free /models list, not a paid call
        except urllib.error.HTTPError as e:
            # ONLY a missing /models endpoint (Cloudflare 405s, Perplexity 404s) falls back to
            # the hand-refreshed static list — an auth error (401/403) must NOT be masked as
            # working seats that would then fail at --panel time.
            ids = STATIC_MODELS.get(prov, []) if e.code in (404, 405) else []
            if not ids:
                continue
        except Exception:  # noqa: BLE001 — unreachable / timed out: skip this provider
            continue
        ranked = sorted({i for i in ids if _suitable(i)}, key=lambda i: (_version(i), i), reverse=True)
        for n, mid in enumerate(ranked):
            name = mid.replace("models/", "")
            seen.add(name)
            # A multi-lineage provider (Cloudflare, Ollama Cloud) serves many families:
            # the seat's lineage comes from the model id, not the provider label.
            lin = infer_lineage(name, "") if lineage == "(varies)" else lineage
            row = [lin.lower(), name, base, "paid", "unprobed"]       # paid stays UNPROBED (consent-gated)
            catalog.setdefault(name, row)             # full catalog: --choose can name any servable model
            if name not in listed and n < 4:          # top-4 per provider in the BROWSE table
                table.append(row); listed.add(name)
    return table, seen, catalog


def do_configure(project, explicit, auto):
    """PICK + REMEMBER your panel: configured providers -> grouped-by-lineage table -> pick
    1-3 (or the score-ranked, free-first SUGGESTION via Enter / --auto) -> remember it. Paid
    models are listed UNPROBED (no auto-spend); free/local scores come from the registry."""
    prior = read_panel()
    rows, seen, catalog = _candidate_rows()
    if not rows:
        print("nothing to choose yet — `--probe` a local seat or store a cloud key "
              "(`critic_setup.py --install`), then re-run `--configure`.")
        print("(meanwhile, fall back to same-lineage in-context critics — the Standard "
              "preset's personas — and FLAG 'independence degraded'.)")
        return 1
    if prior and not explicit and not auto:             # keep-or-update + new-model flag
        cur = ", ".join(s["model"] for s in prior.get("selected", []))
        new = sorted(set(seen) - set(prior.get("seen", [])))
        print(f"current panel: {cur or '(empty)'}   (chosen {_panel_age_days(prior)}d ago)")
        if new:
            print(f"⚑ {len(new)} new model(s) since last check: {', '.join(new[:6])}")
        if sys.stdin.isatty() and input("keep it? [Y/n] ").strip().lower() not in ("n", "no"):
            print("kept.")
            return 0

    by_lin = {}
    for r in rows:
        by_lin.setdefault(r[0], []).append(r)
    flat = []
    print("\nAvailable critics (grouped by lineage — pick 1-3, ideally one per lineage):")
    for lin in sorted(by_lin):
        print(f"  {lin}:")
        for r in by_lin[lin]:
            flat.append(r)
            print(f"    [{len(flat)}] {r[1]:34} {r[3]:5} score={r[4]}")
    suggestion = _suggest_panel(rows)
    sug = ",".join(str(flat.index(r) + 1) for r in suggestion)
    print(f"  suggested (score-ranked, free-first, one per lineage): [{sug}] -> "
          f"{', '.join(r[1] for r in suggestion)}")

    if explicit:
        want = [c.strip() for c in explicit.split(",") if c.strip()]
        picks = [catalog[m] for m in want if m in catalog]   # match the FULL catalog, not just the table
    elif auto:
        picks = suggestion
    elif sys.stdin.isatty():
        raw = input(f"\npick numbers (e.g. 1,3), or Enter for the suggested [{sug}]: ")
        if not raw.strip():
            picks = suggestion
        else:
            idx = [int(x) for x in re.findall(r"\d+", raw)]
            picks = [flat[i - 1] for i in idx if 1 <= i <= len(flat)]
    else:
        print('\nnon-interactive: pass `--choose "m1,m2"` or `--auto` (take the suggestion). nothing saved.')
        return 1

    if not 1 <= len(picks) <= 3:
        print(f"pick 1-3 (got {len(picks)}). nothing saved.")
        return 1
    lins = [p[0] for p in picks]
    if len(set(lins)) < len(lins):
        print("note: two picks share a lineage — that lowers decorrelation (a panel wants diverse families).")
    selected = [{"model": p[1], "lineage": p[0], "endpoint": p[2], "cost": p[3], "score": p[4]} for p in picks]
    path = write_panel(selected, seen, project)
    print(f"\n✓ saved {len(selected)}-critic panel -> {path}")
    for s in selected:
        spend = "" if s["cost"] == "free" else "  [PAID — --panel asks before spending]"
        print(f"    {s['model']}  [{s['lineage']}]  {s['cost']}  score={s['score']}{spend}")
    print("Run it:  python3 external_critic.py <file> --panel")
    return 0


# --- Run the remembered panel: each chosen seat critiques; the skill synthesizes ----
# --configure REMEMBERS a panel; --panel RUNS it. Local seats use native Ollama; a cloud
# seat loads its provider's stored key (read-only) and is spend-gated. This script only
# RUNS the seats — dedupe / preserve-list / contested (the synthesis) stays the skill's job.
def _provider_for_endpoint(endpoint):
    e = (endpoint or "").rstrip("/")
    for prov, (_lin, base) in PROVIDERS.items():
        base = resolve_base(base)
        if base and base.rstrip("/") == e:
            return prov
    return None


# The single-seat cloud path keeps the docs' promise: a key stored once in the OS
# secret store (critic-api-key-<provider>) is found WITHOUT any shell helper.
# Env / .env CRITIC_API_KEY still wins; this only fills the gap when CRITIC_BASE_URL
# identifies a known provider. (--panel seats already resolve keys via _key_for.)
if BASE_URL and not API_KEY:
    API_KEY = _provider_key(_provider_for_endpoint(BASE_URL)) or ""
    if not API_KEY and not re.search(r"localhost|127\.0\.0\.1", BASE_URL):
        print("(advisory: no CRITIC_API_KEY set and CRITIC_BASE_URL matches no known "
              "provider — sending keyless; a keyed endpoint will refuse)", file=sys.stderr)


def _seat_runtime(seat):
    """A remembered seat -> (model, base_url, api_key). Native Ollama (base_url='') UNLESS
    the endpoint is OpenAI-compatible — a known provider, a '/vN' path (a cloud base, or a
    local server like LM Studio / vLLM on :1234/v1), or the active BASE_URL — in which case
    it's called OpenAI-compat with that provider's key via _key_for. Classifying by endpoint
    SHAPE (not 'localhost') is what lets a local /v1 server and a LAN Ollama both work."""
    model = seat.get("model", "")
    endpoint = seat.get("endpoint", "") or HOST
    prov = _provider_for_endpoint(endpoint)
    openai_compat = bool(prov) or bool(re.search(r"/v\d", endpoint)) or \
        (bool(BASE_URL) and endpoint.rstrip("/") == BASE_URL.rstrip("/"))
    if not openai_compat:
        return model, "", ""          # native Ollama (call_model posts to HOST/api/chat)
    return model, endpoint, _key_for(prov, endpoint)


def do_panel(artifact_path, brief, intent, mode, depth, assume_yes):
    """Run the REMEMBERED panel (--configure): critique the artifact with each chosen seat
    and print every view as a CONTESTED input for the framework's spatial synthesis
    (agreement = corroboration; a lone claim = contested — you are the reducer). Paid seats
    are spend-gated: confirmed, --yes, or skipped (never an auto-spend)."""
    panel = read_panel()
    if not panel or not panel.get("selected"):
        print("no remembered panel — run `--configure` to pick one (`--auto` for the suggested "
              "default). `--panel` runs only a panel you chose.")
        return 1
    try:
        art = sys.stdin.read() if artifact_path == "-" else open(artifact_path, encoding="utf-8").read()
    except OSError as e:
        sys.exit(f"cannot read {artifact_path}: {e}")
    system = SYSTEM + (DEPTH_FULL if depth == "full" else "")
    prompt = build_prompt(art, brief, intent, mode)
    label_art = "<stdin>" if artifact_path == "-" else artifact_path
    print(f"PANEL — {len(panel['selected'])} remembered seat(s) on {os.path.basename(label_art)}:")
    ran = 0
    for seat in panel["selected"]:
        model, base_url, api_key = _seat_runtime(seat)
        label = f"{model} [{seat.get('lineage', '?')}]"
        if seat.get("cost") == "paid":
            if not api_key:
                prov = _provider_for_endpoint(seat.get("endpoint", "")) or "<provider>"
                print(f"\n--- SKIP {label}: paid seat — no key stored. Enable it: "
                      f"`critic_setup.py --provider {prov}` (stores the key), then re-run. ---")
                continue
            if not assume_yes:
                if not sys.stdin.isatty():
                    print(f"\n--- SKIP {label}: PAID seat, non-interactive (re-run with --yes to spend) ---")
                    continue
                if input(f"\nRun PAID seat {label}? this spends on your key [y/N] ").strip().lower() not in ("y", "yes"):
                    print("  skipped.")
                    continue
        print(f"\n=== PANEL CRITIC: {label}  ({base_url or HOST}) ===")
        try:
            out = call_model(system, prompt, model=model, base_url=base_url, api_key=api_key)
        except Exception as e:  # noqa: BLE001 — one dead seat must not sink the panel
            print(f"(unavailable: {e})")
            continue
        print(out.strip())
        log_run(label_art, mode, depth, brief, intent,
                model=model, endpoint=(base_url or HOST), base_url=base_url)
        ran += 1
    if not ran:
        print("\nno seat produced a critique (all skipped/unavailable). Check your keys, "
              "Ollama, or `--configure`.")
        return 1
    print(f"\n=== {ran} seat(s) ran. SYNTHESIZE (don't average): agreement across seats is strong "
          "corroboration; a lone claim is a CONTESTED point to weigh — you are the reducer. ===")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Independent critique via local Ollama or an OpenAI-compatible endpoint.")
    ap.add_argument("artifact", nargs="?",
                    help="path to the work under review, or '-' for stdin")
    ap.add_argument("--brief", default="", help="what the critic should focus on")
    ap.add_argument("--intent", default="", help="the externalized intent spec")
    ap.add_argument("--mode", default="correctness",
                    choices=["correctness", "taste"])
    ap.add_argument("--depth", default="brief", choices=["brief", "full"],
                    help="brief (default) = terse contract; full = +rationale per finding")
    ap.add_argument("--no-log", action="store_true",
                    help="don't record this run in the critique log")
    ap.add_argument("--probe", action="store_true",
                    help="capability probe (availability != capability): SCORE the seat on a "
                         "tiny multi-flaw artifact (PASS = score>=1); records it in the registry")
    ap.add_argument("--discover", action="store_true",
                    help="list the models this key/endpoint can serve (newest-first), with "
                         "cost tier + capability score — don't hard-code a model")
    ap.add_argument("--configure", action="store_true",
                    help="PICK + REMEMBER your panel: configured providers -> grouped table -> "
                         "pick 1-3 (or --auto for the suggested default); flags new models")
    ap.add_argument("--auto", action="store_true",
                    help="with --configure: accept the suggested (score-ranked, free-first) panel")
    ap.add_argument("--project", action="store_true",
                    help="with --configure: save the panel project-locally (./.critic/) not globally")
    ap.add_argument("--choose", default="",
                    help='with --configure (non-interactive): comma-separated model ids to select')
    ap.add_argument("--cost", choices=["free", "paid"], default="",
                    help="override the inferred cost label recorded by --probe")
    ap.add_argument("--expect", default="",
                    help='for a faithful `--probe FILE`: comma-separated word(s) a '
                         "genuine critic must say when it finds the flaw you planted")
    ap.add_argument("--panel", action="store_true",
                    help="run the REMEMBERED panel (--configure) against the artifact: each "
                         "chosen seat critiques; paid seats spend-gated (--yes to allow)")
    ap.add_argument("--yes", action="store_true",
                    help="with --panel: run PAID seats without the per-seat spend confirm")
    args = ap.parse_args()

    if args.configure:
        sys.exit(do_configure(args.project, args.choose, args.auto))
    if args.discover:
        sys.exit(do_discover())
    if args.probe:
        sys.exit(do_probe(args.cost, args.artifact or "", args.expect))
    if args.panel:
        if not args.artifact:
            ap.error("--panel needs an artifact path (or '-' for stdin)")
        sys.exit(do_panel(args.artifact, args.brief, args.intent, args.mode, args.depth, args.yes))
    if not args.artifact:
        ap.error("artifact is required (or pass --configure / --discover / --probe / --panel)")

    if args.artifact == "-":
        text = sys.stdin.read()
    else:
        with open(args.artifact, encoding="utf-8") as f:
            text = f.read()

    # Advisory: has this seat been certified capable? (availability != capability)
    _seat = latest_per_model(_registry_records()).get(MODEL)
    if not _seat or _seat.get("probe") != "PASS":
        print(f"(advisory: '{MODEL}' has no capability-PASS on record — run "
              f"`python3 {os.path.basename(__file__)} --probe` to certify it; a reachable "
              f"seat can still be a null one)", file=sys.stderr)
    elif _stale(_seat.get("date", "")):
        print(f"(advisory: '{MODEL}' capability-PASS is stale — re-probe; tags mutate)",
              file=sys.stderr)
    # Cheap date-compare only (no network): nudge to re-check for new models periodically.
    _pn = read_panel()
    if _pn and _panel_age_days(_pn) > REFRESH_DAYS:
        print(f"(advisory: critic panel is {_panel_age_days(_pn)}d old — run `--configure` to "
              f"check for newer models)", file=sys.stderr)

    system = SYSTEM + (DEPTH_FULL if args.depth == "full" else "")
    try:
        out = call_model(system, build_prompt(text, args.brief, args.intent, args.mode))
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
            args.mode, args.depth, args.brief, args.intent):
        print(f"(logged: {MODEL} -> {LOG_PATH})", file=sys.stderr)


if __name__ == "__main__":
    main()
