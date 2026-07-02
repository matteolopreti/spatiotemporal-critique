#!/usr/bin/env python3
"""trial_runner.py — the measurement Trial (see ROADMAP.md).

Measures, instead of arguing, the skill's two central claims:
  (1) the protocol contract beats a lone flaw-hunting critic;
  (2) a lineage-diverse panel beats the best single seat.

Design (stdlib only, deterministic grading — no LLM judges an LLM):
  - trials/manifest.json: planted-defect artifacts + clean DECOYS (the decoys
    measure INVENTED problems — the protocol's core promise is fewer of them).
  - Decorrelated authorship: a seat is never scored on artifacts its own
    lineage authored (an author knows its own answer key).
  - Grading reuses the floor probe's discipline: a flaw is NAMED when a
    sentence (or adjacent pair) pairs one of its subject anchors with a fault
    word (per-flaw crit list + PROBE_CRITICAL). Findings are counted from
    "[severity" markers, which every condition's contract requests.
  - Conditions: lone (flaw-hunting persona) · protocol (the panel seat
    contract) · quick (the Quick preset). The PANEL row is the union of the
    protocol condition across seats — no extra calls, exactly what --panel
    hands the reducer. Panel invented-problems are summed un-deduped: that is
    honestly what the reducer must wade through.

Success criteria (stated in ROADMAP.md before this was run): the panel earns
its cost only if it beats the best single seat on recall WITHOUT a worse
invented-problem rate.

Usage:  python3 trial_runner.py            # run everything (writes trials/results/)
        python3 trial_runner.py --report   # re-score saved responses only
"""
import json
import os
import re
import sys
import threading

import external_critic as ec

HERE = os.path.dirname(os.path.abspath(__file__))
TRIALS = os.path.join(HERE, "trials")
RESULTS = os.path.join(TRIALS, "results")

# seat -> (model, base_url, author-lineage-to-exclude)
SEATS = {
    "gemma": ("gemma4:12b-mlx", ""),
    "codex": ("codex-default", "codex-cli"),
}

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
# The v5.0 "protocol-as-brief" condition (pre-registered in ROADMAP.md): the Standard
# preset shipped whole to a non-Claude seat. If this doesn't beat the plain seat
# contract, a full protocol-as-harness won't either.
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
CONDITIONS = {"lone": LONE, "protocol": ec.SYSTEM, "quick": QUICK, "standard": STANDARD}
BRIEF = "Review this work."


def findings_count(text):
    return len(re.findall(r"\[\s*severity", text or "", re.I))


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


def _resp_path(seat, art, cond):
    return os.path.join(RESULTS, f"{seat}__{os.path.splitext(art)[0]}__{cond}.txt")


def run_seat(seat, arts, report_only):
    model, base = SEATS[seat]
    for art in arts:
        if art["author"] == seat:
            continue                    # never scored on your own answer key
        text = open(os.path.join(TRIALS, art["file"]), encoding="utf-8").read()
        for cond, system in CONDITIONS.items():
            path = _resp_path(seat, art["file"], cond)
            if os.path.exists(path) or report_only:
                continue
            mode = "correctness"
            prompt = ec.build_prompt(text, BRIEF, "", mode)
            try:
                out = ec.call_model(system, prompt, model=model, base_url=base, api_key="")
            except Exception as e:  # noqa: BLE001 — record the failure, keep going
                out = f"(seat unavailable: {e})"
            with open(path, "w", encoding="utf-8") as f:
                f.write(out)
            print(f"  done {seat:6} {art['file']:16} {cond}", flush=True)


def score(arts):
    rows = {}   # (cond, seat) -> dict(named, flaws, findings, decoy_findings)
    per_artifact_named = {}  # (cond, art) -> set(labels across seats)  [panel union]
    for seat in SEATS:
        for art in arts:
            if art["author"] == seat:
                continue
            for cond in CONDITIONS:
                path = _resp_path(seat, art["file"], cond)
                if not os.path.exists(path):
                    continue
                out = open(path, encoding="utf-8").read()
                if out.startswith("(seat unavailable"):
                    continue
                k = (cond, seat)
                r = rows.setdefault(k, {"named": 0, "flaws": 0, "findings": 0,
                                        "decoy_findings": 0, "decoys": 0})
                n = findings_count(out)
                if art["decoy"]:
                    r["decoy_findings"] += n
                    r["decoys"] += 1
                else:
                    named = flaws_named(out, art["flaws"])
                    r["named"] += len(named)
                    r["flaws"] += len(art["flaws"])
                    r["findings"] += n
                    per_artifact_named.setdefault((cond, art["file"]), set()).update(named)
    return rows, per_artifact_named


def main():
    report_only = "--report" in sys.argv
    os.makedirs(RESULTS, exist_ok=True)
    arts = json.load(open(os.path.join(TRIALS, "manifest.json")))["artifacts"]
    if not report_only:
        threads = [threading.Thread(target=run_seat, args=(s, arts, report_only)) for s in SEATS]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    rows, union = score(arts)

    total_flaws = sum(len(a["flaws"]) for a in arts)
    print(f"\nTRIAL SCOREBOARD — {len(arts)} artifacts, {total_flaws} planted flaws, "
          f"{sum(1 for a in arts if a['decoy'])} clean decoys (battery trial-v1)")
    print(f"{'condition':10} {'seat':7} {'recall':>12} {'precision':>12} {'invented/decoy':>15}")
    for (cond, seat), r in sorted(rows.items()):
        rec = f"{r['named']}/{r['flaws']}"
        prec = f"{r['named']}/{r['findings']}" if r["findings"] else "—"
        inv = f"{r['decoy_findings']}/{r['decoys']}" if r["decoys"] else "—"
        print(f"{cond:10} {seat:7} {rec:>12} {prec:>12} {inv:>15}")

    # PANEL = union of the protocol condition across seats (what --panel hands the reducer)
    panel_named = sum(len(v) for (c, f), v in union.items()
                      if c == "protocol" and not next(a for a in arts if a["file"] == f)["decoy"])
    panel_inv = sum(r["decoy_findings"] for (c, s), r in rows.items() if c == "protocol")
    panel_dec = sum(r["decoys"] for (c, s), r in rows.items() if c == "protocol")
    # a flaw counts once per artifact-union; denominator = flaws on artifacts ANY seat reviewed
    reviewed = {f for (c, f) in union if c == "protocol"}
    panel_flaws = sum(len(a["flaws"]) for a in arts if a["file"] in reviewed)
    print(f"{'panel':10} {'union':7} {str(panel_named) + '/' + str(panel_flaws):>12} "
          f"{'—':>12} {str(panel_inv) + '/' + str(panel_dec):>15}")
    print("\nRaw responses: trials/results/ — re-score anytime with `python3 trial_runner.py --report`.")


if __name__ == "__main__":
    main()
