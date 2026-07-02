#!/usr/bin/env python3
"""trial_runner.py — the measurement Trial (see ROADMAP.md, results in TRIAL.md).

Measures, instead of arguing, the skill's central claims:
  (1) the protocol contract beats a lone flaw-hunting critic;
  (2) a lineage-diverse panel beats the best single seat;
  (3) [battery v2] whether a full protocol-as-harness beats the shipped panel
      — the v5.0 gate experiment.

Design (stdlib only, deterministic grading — no LLM judges an LLM):
  - trials/manifest.json (battery v1) and trials/v2/manifest.json (battery v2):
    planted-defect artifacts + clean DECOYS (decoys measure INVENTED problems —
    the protocol's core promise is fewer of them).
  - Decorrelated authorship: a seat is never scored on artifacts its own
    lineage authored (an author knows its own answer key).
  - Grading reuses the floor probe's discipline: a flaw is NAMED when a
    sentence (or adjacent pair) pairs one of its subject anchors with a fault
    word (per-flaw crit list + PROBE_CRITICAL). A FINDING is a "[severity"
    marker; when a response uses none, the counter falls back to list items
    inside its ISSUES/GENERIC section (battery v1 showed marker-only counting
    undercounts some seats).
  - Conditions: lone (flaw-hunting persona) · protocol (the panel seat
    contract) · quick (Quick preset) · standard (Standard preset as brief) ·
    harness (battery v2 only: the ENTIRE PROTOCOL.md as the orchestrator
    contract — the protocol-as-harness proxy). The PANEL row is the union of
    the protocol condition across seats — exactly what --panel hands the
    reducer; its decoy findings are summed un-deduped (what the reducer must
    actually wade through).

Success criteria live in ROADMAP.md, stated before each battery ran.

Usage:  python3 trial_runner.py [--battery v1|v2]     # run (idempotent; skips existing responses)
        python3 trial_runner.py --report [--battery v2]  # re-score saved responses only
"""
import json
import os
import re
import sys
import threading

import external_critic as ec

HERE = os.path.dirname(os.path.abspath(__file__))

GOOGLE_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
# seat -> (model, base_url, key_provider)  — key resolved from the OS secret store at runtime
ALL_SEATS = {
    "gemma": ("gemma4:12b-mlx", "", ""),
    "codex": ("codex-default", "codex-cli", ""),
    "gemini": ("gemini-3.5-flash", GOOGLE_BASE, "google"),
}
BATTERY_SEATS = {"v1": ("gemma", "codex"), "v2": ("gemma", "codex", "gemini"),
                 "v3": ("gemma", "codex", "gemini"), "v3cert": ("gemma", "codex", "gemini")}

LONE = ("You are a strict, uncompromising reviewer. Your job is to find the problems "
        "in the work. List every problem you can find, each as: [severity high/med/low] "
        "the problem — a concrete fix. End with one line: VERDICT — ship or don't ship, and why.")
QUICK = ("Answer these six about the work, then stop:\n"
         "1. What's working here that must be preserved?\n"
         "2. Steelman the current choices — where might they already be right?\n"
         "3. State what the author is actually trying to achieve, as a specific consequential claim.\n"
         "4. List the assumptions you're making where things are unspecified, and what breaks if each is wrong.\n"
         "5. The 3 highest-leverage issues only, each as: [severity high/med/low] the problem — "
         "a concrete fix. Abstain explicitly where you can't judge instead of filling.\n"
         "6. Verdict: is this genuinely better than leaving it as is?")
STANDARD = ("Run this review procedure on the work, in order, then stop:\n"
            "1. Preserve-list: what's working that must survive any edit?\n"
            "2. Steelman each current choice; drop any critique the choice survives.\n"
            "3. State the author's actual goal as a falsifiable claim, and stress it against one "
            "wrong-but-plausible alternative reading.\n"
            "4. Assumptions you're making where things are unspecified, each with what breaks if wrong.\n"
            "5. Review from ~3 in-context angles (domain expert · skeptical generalist · end user) — "
            "then merge them, marking genuine disagreement as contested rather than resolving it.\n"
            "6. Highest-leverage issues, ranked by leverage (severity × confidence × blast-radius), "
            "each as: [severity high/med/low] the problem — a concrete fix. Abstain explicitly where "
            "you can't judge instead of filling.\n"
            "7. Backward check: skip — no edit history is provided; do not invent one.\n"
            "8. Verdict: genuinely better than leaving it as is — and is there a smaller change that "
            "captures most of the gain?")


def harness_contract():
    """Battery v2's protocol-as-harness proxy: the whole spec as the orchestrator brief."""
    spec = open(os.path.join(HERE, "PROTOCOL.md"), encoding="utf-8").read()
    return (spec + "\n\n---\nYou are the ORCHESTRATOR: execute the protocol above, alone, on the "
            "work in the next message. Run the applicable awake stages in one pass (no real edit "
            "history is provided — skip the backward-temporal check rather than inventing one), "
            "then emit: PRESERVE; then ISSUES, each item as '[severity high/med/low] the problem — "
            "a concrete fix' (abstain explicitly where you can't judge); then VERDICT. The final "
            "decision belongs to the human owner — never render a green light.")


# Battery v3 (docs/08 plan, E2): the deterministic quote gate's prompt half. The gate
# itself runs at SCORING time on the raw response — pre-gate output is always preserved.
QUOTE_ADDENDUM = (
    "\n\nADDITIONAL OUTPUT CONTRACT — evidence grounding: every ISSUES item MUST include, "
    "on its own lines directly under the item:\n"
    'QUOTE: "<verbatim excerpt copied exactly from the work>"\n'
    "WHY: <one sentence on why this quote entails the problem>\n"
    "Use more than one QUOTE line when a single excerpt is not enough. A finding whose "
    "QUOTE does not appear verbatim in the work is discarded unread — never paraphrase "
    "inside QUOTE."
)


def conditions_for(battery):
    if battery in ("v3", "v3cert"):
        return {"protocol": ec.SYSTEM, "protocolq": ec.SYSTEM + QUOTE_ADDENDUM}
    conds = {"lone": LONE, "protocol": ec.SYSTEM, "quick": QUICK, "standard": STANDARD}
    if battery == "v2":
        conds["harness"] = harness_contract()
    return conds


BRIEF = "Review this work."


def findings_count(text):
    """Format-robust finding counter (battery v1 lesson: markers alone undercount).
    Primary: '[severity' markers. Fallback: list items inside the ISSUES/GENERIC block."""
    n = len(re.findall(r"\[\s*severity", text or "", re.I))
    if n:
        return n
    m = re.search(r"(?:ISSUES|GENERIC)\b(.*?)(?:\bVERDICT\b|\bREASONING\b|$)",
                  text or "", re.S | re.I)
    if m:
        return len(re.findall(r"^\s*(?:[-*•]|\d+[.)])\s+\S", m.group(1), re.M))
    return 0


# Floor against trivially-matching micro-quotes ("def ", "the") that would let a
# fabricated finding pass the gate on a 4-char excerpt. Over-strictness is measured,
# not assumed: the per-seat quote-emission-failure metric (docs/08 E2) catches it.
QUOTE_MIN_CHARS = 10


def _norm(s):
    """Whitespace-collapsed, quote-normalized, lowercased — the gate's match space."""
    for a, b in (("“", '"'), ("”", '"'), ("«", '"'), ("»", '"'), ("„", '"'),
                 ("‘", "'"), ("’", "'"), ("‚", "'"), ("`", "")):
        s = (s or "").replace(a, b)
    return re.sub(r"\s+", " ", s).lower().strip()


def split_findings(text):
    """Split a response into per-finding chunks (QUOTE:/WHY: lines stay with their item)."""
    t = ec._strip_reasoning(text or "")
    chunks = re.split(r"(?=\[\s*severity)", t, flags=re.I)
    if len(chunks) > 1:
        return chunks[1:]
    m = re.search(r"(?:ISSUES|GENERIC)\b(.*?)(?:\bVERDICT\b|\bREASONING\b|$)", t, re.S | re.I)
    if not m:
        return []
    parts = re.split(r"(?m)^(?=\s*(?:[-*•]|\d+[.)])\s+\S)", m.group(1))
    return [p for p in parts if re.match(r"\s*(?:[-*•]|\d+[.)])\s+\S", p)]


def quote_gate(text, artifact_text):
    """Deterministic quote-existence gate (docs/08 E2): keep a finding iff at least one
    of its QUOTE lines exists verbatim (normalized) in the artifact. Returns
    (kept_chunks, dropped_count). Raw responses are never modified — re-scorable."""
    art = _norm(artifact_text)
    kept, dropped = [], 0

    def payload(q):
        # normalize FIRST (turns «»/“” wrappers into straight quotes), then strip the
        # wrappers — a quote emitted as QUOTE: «x» must match an unquoted x in the work
        return _norm(q).strip('"').strip("'").strip()

    for ch in split_findings(text):
        # \b not ^: seats emit "— QUOTE: …" inline as often as on its own line; a stray
        # capture is harmless (it just won't match the artifact)
        qs = re.findall(r"(?im)\bquote:\s*(.+?)\s*$", ch)
        if any(len(payload(q)) >= QUOTE_MIN_CHARS and payload(q) in art for q in qs):
            kept.append(ch)
        else:
            dropped += 1
    return kept, dropped


def flaws_named(text, flaws):
    """Deterministic per-flaw grading — same window discipline as score_probe."""
    answer = ec._strip_reasoning(text or "")
    sents = [s.lower() for s in re.split(r"[.\n;!?]+", answer) if s.strip()]
    windows = sents + [sents[i] + " " + sents[i + 1] for i in range(len(sents) - 1)]
    named = []
    for fl in flaws:
        crit = tuple(c.lower() for c in fl.get("crit", ())) + ec.PROBE_CRITICAL
        anchors = [a.lower() for a in fl["anchors"]]
        if any(any(a in w for a in anchors) and any(c in w for c in crit) for w in windows):
            named.append(fl["label"])
    return named


def run_seat(seat, arts, conds, trials_dir, results_dir):
    model, base, key_prov = ALL_SEATS[seat]
    api_key = (ec._provider_key(key_prov) or "") if key_prov else ""
    for art in arts:
        if art["author"] == seat:
            continue                    # never scored on your own answer key
        text = open(os.path.join(trials_dir, art["file"]), encoding="utf-8").read()
        stem = os.path.splitext(os.path.basename(art["file"]))[0]
        for cond, system in conds.items():
            path = os.path.join(results_dir, f"{seat}__{stem}__{cond}.txt")
            if os.path.exists(path):
                continue
            prompt = ec.build_prompt(text, BRIEF, "", "correctness")
            try:
                out = ec.call_model(system, prompt, model=model, base_url=base, api_key=api_key)
            except Exception as e:  # noqa: BLE001 — record the failure, keep going
                out = f"(seat unavailable: {e})"
            with open(path, "w", encoding="utf-8") as f:
                f.write(out)
            print(f"  done {seat:6} {art['file']:16} {cond}", flush=True)


def score(arts, seats, conds, results_dir, trials_dir):
    rows = {}
    union = {}   # (cond, artifact) -> set(labels)  [panel = union of `protocol`]
    for seat in seats:
        for art in arts:
            if art["author"] == seat:
                continue
            stem = os.path.splitext(os.path.basename(art["file"]))[0]
            for cond in conds:
                path = os.path.join(results_dir, f"{seat}__{stem}__{cond}.txt")
                if not os.path.exists(path):
                    continue
                out = open(path, encoding="utf-8").read()
                if out.startswith("(seat unavailable"):
                    continue
                r = rows.setdefault((cond, seat), {"named": 0, "flaws": 0, "findings": 0,
                                                   "decoy_findings": 0, "decoys": 0,
                                                   "gate_dropped": 0, "gate_recall_lost": 0})
                gated = cond.endswith("q")
                if gated:
                    artifact = open(os.path.join(trials_dir, art["file"]), encoding="utf-8").read()
                    kept, dropped = quote_gate(out, artifact)
                    graded, n = "\n".join(kept), len(kept)
                    r["gate_dropped"] += dropped
                    miss = findings_count(out) - (len(kept) + dropped)
                    if miss > 0:   # findings the counter sees but the chunker missed —
                        print(f"(parse mismatch: {os.path.basename(path)} — {miss} findings "
                              f"invisible to the gate; inspect before trusting this row)",
                              file=sys.stderr)
                else:
                    graded, n = out, findings_count(out)
                if art["decoy"]:
                    r["decoy_findings"] += n
                    r["decoys"] += 1
                else:
                    named = flaws_named(graded, art["flaws"])
                    if gated:   # a true flaw named pre-gate but dropped by it = the gate's own recall cost
                        r["gate_recall_lost"] += len(set(flaws_named(out, art["flaws"])) - set(named))
                    r["named"] += len(named)
                    r["flaws"] += len(art["flaws"])
                    r["findings"] += n
                    union.setdefault((cond, art["file"]), set()).update(named)
    return rows, union


def main():
    battery = next((b for b in ("v3cert", "v3", "v2") if b in sys.argv), "v1")
    report_only = "--report" in sys.argv
    dirs = {"v1": ("trials",), "v2": ("trials", "v2"),
            "v3": ("trials", "v3"), "v3cert": ("trials", "v3", "cert")}
    trials_dir = os.path.join(HERE, *dirs[battery])
    if battery == "v3cert" and not report_only and "--unseal" not in sys.argv:
        sys.exit("SEALED: the certification set runs once, at E6 (docs/08 plan). "
                 "Pass --unseal only for that one pre-registered run.")
    results_dir = os.path.join(trials_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    arts = json.load(open(os.path.join(trials_dir, "manifest.json")))["artifacts"]
    seats = BATTERY_SEATS[battery]
    conds = conditions_for(battery)
    if not report_only:
        threads = [threading.Thread(target=run_seat, args=(s, arts, conds, trials_dir, results_dir))
                   for s in seats]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    rows, union = score(arts, seats, conds, results_dir, trials_dir)

    total_flaws = sum(len(a["flaws"]) for a in arts)
    print(f"\nTRIAL SCOREBOARD — battery {battery}: {len(arts)} artifacts, {total_flaws} planted "
          f"flaws, {sum(1 for a in arts if a['decoy'])} clean decoys")
    print(f"{'condition':10} {'seat':7} {'recall':>12} {'findings':>10} {'invented/decoy':>15} "
          f"{'gate(drop/rloss)':>17}")
    for (cond, seat), r in sorted(rows.items()):
        rec = f"{r['named']}/{r['flaws']}"
        inv = f"{r['decoy_findings']}/{r['decoys']}" if r["decoys"] else "—"
        gate = (f"{r['gate_dropped']}/{r['gate_recall_lost']}" if cond.endswith("q") else "—")
        print(f"{cond:10} {seat:7} {rec:>12} {r['findings']:>10} {inv:>15} {gate:>17}")

    for cond in ("protocol", "protocolq", "harness"):
        if not any(c == cond for (c, _f) in union):
            continue
        named = sum(len(v) for (c, f), v in union.items()
                    if c == cond and not next(a for a in arts if a["file"] == f)["decoy"])
        reviewed = {f for (c, f) in union if c == cond}
        denom = sum(len(a["flaws"]) for a in arts if a["file"] in reviewed)
        inv = sum(r["decoy_findings"] for (c, s), r in rows.items() if c == cond)
        dec = sum(r["decoys"] for (c, s), r in rows.items() if c == cond)
        print(f"{'panel(' + cond + ')':18} {str(named) + '/' + str(denom):>11} "
              f"{'':>10} {str(inv) + '/' + str(dec):>15}")
    print(f"\nRaw responses: {os.path.relpath(results_dir, HERE)}/ — re-score with "
          f"`python3 trial_runner.py --report --battery {battery}`.")


if __name__ == "__main__":
    main()
