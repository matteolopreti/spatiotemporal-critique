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
    # quantitative proxy that ranks the --select panel. Deterministic, non-LLM grader.

    python3 external_critic.py --select
    # PANEL: up to 3 capable seats across DISTINCT lineages (independence = diversity),
    # ranked by score, free-first; paid seats flagged to confirm the spend; none capable
    # -> same-lineage fallback flagged "independence degraded".

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
    CRITIC_REGISTRY default: critic_registry.tsv next to this script — the
                   capability-probe log {date · model · lineage · probe · cost}.
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
import re
import sys
import urllib.error
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


def call_model(system, prompt):
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    headers = {"Content-Type": "application/json"}
    if BASE_URL:  # OpenAI-compatible endpoint (cloud, or any local /v1 server)
        url = f"{BASE_URL.rstrip('/')}/chat/completions"
        body = {"model": MODEL, "messages": messages, "stream": False, **OPENAI_OPTIONS}
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"
        path = ("choices", 0, "message", "content")
    else:         # Ollama native (default; private, on localhost)
        url = f"{HOST}/api/chat"
        body = {"model": MODEL, "messages": messages, "stream": False, "options": OPTIONS}
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


def log_run(artifact, mode, depth, brief, intent):
    """Pin-and-log: record which model (and sampling params) produced which
    critique — the logged-trace discipline the Temporal axis and ledger use.
    depth is logged too: it changes the prompt, so it's part of reproducibility.
    Returns True if the record was written."""
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    seed = "na" if BASE_URL else OPTIONS["seed"]  # seed isn't sent on the cloud path
    rec = (f"{ts}\tmodel={MODEL}\tendpoint={ENDPOINT}\tmode={mode}\tdepth={depth}"
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
# a quantitative proxy that RANKS seats for the --select panel (a misrank only reorders
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
        ("gemini", ("gemini", "generativelanguage", "googleapis")),
        ("gpt", ("gpt-", "openai.com", "o1-", "o3-", "o4-")),
        ("deepseek", ("deepseek",)),
        ("glm", ("glm", "z.ai", "zhipu", "bigmodel")),
        ("mistral", ("mistral", "mixtral", "magistral")),
        ("qwen", ("qwen",)),
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


def do_select(top=3):
    """Stage 4: a PANEL of up to `top` capable seats across DISTINCT lineages
    (independence = diversity — 3 of one family share a blind spot), ranked by
    capability score, then free-first, then recency. Free seats are usable now; a
    paid seat is flagged to confirm the spend (the ladder, generalized to a panel)."""
    latest = latest_per_model(_registry_records())
    if not latest:
        print("no capability records yet. Run `--probe` against a different-lineage seat "
              "first (see EXTERNAL_CRITIC.md -> Capability detection).")
        return 1
    capable = [r for r in latest.values()
               if r.get("probe") == "PASS"
               and r.get("lineage") not in ("claude", "anthropic", "unknown")]
    if not capable:
        print("no capable, different-lineage seat on record -> fall back to the in-harness "
              "decorrelated-reviewer (same-lineage) and FLAG 'independence degraded.'")
        print("Hunt a FREE+capable lineage: `--probe` each free option (local Ollama + "
              "free-tier cloud), then re-run `--select`.")
        return 1

    def rank_key(r):                                # higher score, then free, then newer
        return (_int(r.get("score")), r.get("cost") == "free", r.get("date", ""))

    best = {}                                       # the best seat per DISTINCT lineage
    for r in capable:
        lin = r["lineage"]
        if lin not in best or rank_key(r) > rank_key(best[lin]):
            best[lin] = r
    panel = sorted(best.values(), key=rank_key, reverse=True)[:top]

    print(f"PANEL — up to {top} capable seats across DISTINCT lineages "
          f"(independence = diversity; weight each by independence, not authority):")
    for i, r in enumerate(panel, 1):
        stale = "  ⚠ STALE — re-probe" if _stale(r.get("date", "")) else ""
        spend = "" if r.get("cost") == "free" else "  [PAID — confirm the spend first]"
        print(f"  {i}. {r['model']}  [{r['lineage']}]  score {r.get('score', '?')}  "
              f"{r.get('cost')}{spend}{stale}")
        print(f"     via {r.get('endpoint')}   (set as CRITIC_MODEL / critic-env)")
    n_free = sum(1 for r in panel if r.get("cost") == "free")
    print(f"\nRun each as a critic and fold every view in as a CONTESTED input. Use the "
          f"{n_free} free seat(s) now; confirm the spend before any PAID seat.")
    if len(panel) < 2:
        print("(only one capable lineage on record — `--probe` more free options for real "
              "decorrelation; a one-seat 'panel' is just a single external critic.)")
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
    ap.add_argument("--select", action="store_true",
                    help="build a PANEL of up to 3 capable seats across distinct lineages "
                         "(ranked by score, free-first) from the capability registry")
    ap.add_argument("--cost", choices=["free", "paid"], default="",
                    help="override the inferred cost label recorded by --probe")
    ap.add_argument("--expect", default="",
                    help='for a faithful `--probe FILE`: comma-separated word(s) a '
                         "genuine critic must say when it finds the flaw you planted")
    args = ap.parse_args()

    if args.probe:
        sys.exit(do_probe(args.cost, args.artifact or "", args.expect))
    if args.select:
        sys.exit(do_select())
    if not args.artifact:
        ap.error("artifact is required (or pass --probe / --select)")

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
