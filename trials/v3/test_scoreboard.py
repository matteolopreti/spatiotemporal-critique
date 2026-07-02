#!/usr/bin/env python3
"""Pins battery v3's PUBLISHED stack-level numbers (TRIAL.md, 2026-07-03) against the
committed frozen responses. The scorer lives in external_critic.py and evolves with the
product — this test makes any historical drift LOUD instead of silent (self-gate
finding, 2026-07-03). Run: python3 trials/v3/test_scoreboard.py"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import trial_runner as tr  # noqa: E402

RDIR = os.path.join(HERE, "results")
arts = json.load(open(os.path.join(HERE, "manifest.json")))["artifacts"]
seats = list(tr.BATTERY_SEATS["v3"])


def cell(seat, art, cond):
    stem = os.path.splitext(os.path.basename(art["file"]))[0]
    p = os.path.join(RDIR, f"{seat}__{stem}__{cond}.txt")
    if not os.path.exists(p):
        return None
    t = open(p, encoding="utf-8").read()
    return None if t.startswith("(seat unavailable") else t


def stacks(arm=None):
    """invented total on clean decoys + panel-union recall for a cumulative stack.
    arm=None -> baseline (protocol); 'gate' -> post-quote-gate; 'K'/'D' -> post-verify."""
    inv = 0
    union = {}
    for seat in seats:
        for art in arts:
            if art["author"] == seat or art.get("retired"):
                continue
            if arm is None:
                out = cell(seat, art, "protocol")
                if out is None:
                    continue
                chunks = None
                n = tr.findings_count(out)
                graded = out
            else:
                out = cell(seat, art, "protocolq")
                if out is None:
                    continue
                text = open(os.path.join(HERE, art["file"]), encoding="utf-8").read()
                chunks, _ = tr.quote_gate(out, text)
                if arm in ("K", "D"):
                    v = cell(seat, art, f"verify{arm}")
                    if chunks and v:
                        verdicts = tr.parse_verdicts(v, len(chunks))
                        chunks = [c for c, k in zip(chunks, verdicts) if k]
                n = len(chunks)
                graded = "\n".join(chunks)
            if art["decoy"]:
                inv += n
            else:
                union.setdefault(art["file"], set()).update(
                    tr.flaws_named(graded, art["flaws"]))
    recall = sum(len(v) for v in union.values())
    return inv, recall


PINNED = {  # (invented_on_clean, panel_union_recall) per stack — published in TRIAL.md
    "baseline": (45, 14),
    "gate": (20, 14),
    "K": (19, 14),
    "D": (8, 14),
}
got = {"baseline": stacks(None), "gate": stacks("gate"), "K": stacks("K"), "D": stacks("D")}
for k, want in PINNED.items():
    assert got[k] == want, f"PUBLISHED NUMBER DRIFTED: {k} expected {want}, scorer now gives {got[k]}"
print("OK — published battery-v3 stack numbers reproduce:",
      {k: v for k, v in got.items()})
