#!/usr/bin/env python3
"""Smallest check that fails if the quote gate breaks (docs/08 E2 measurement path).
Run: python3 trials/v3/test_gate.py — prints OK or raises."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import trial_runner as tr  # noqa: E402

ART = "The cache expires when stored_at plus ttl_seconds is before now."
CASES = [
    # (response, (kept, dropped))
    ('[severity high] wrong expiry — QUOTE: «stored_at plus ttl_seconds»\nWHY: shows it.', (1, 0)),
    ('[severity high] wrong expiry\nQUOTE: "stored_at plus ttl_seconds"\nWHY: shows it.', (1, 0)),
    ('[severity high] wrong expiry — QUOTE: stored_at   plus\tttl_seconds\nWHY: mangled ws.', (1, 0)),
    ('[severity low] bad — QUOTE: "def "\nWHY: micro-quote below the floor.', (0, 1)),
    ('[severity med] invented — QUOTE: "the frobnicator is unbounded"\nWHY: fabricated.', (0, 1)),
    ('[severity med] no quote at all — just an assertion.', (0, 1)),
]

for resp, want in CASES:
    kept, dropped = tr.quote_gate(resp, ART)
    assert (len(kept), dropped) == want, (resp[:50], len(kept), dropped, want)

# fallback chunker: list items inside an ISSUES block, QUOTE lines staying attached
LISTY = ("ISSUES\n- first problem here\n  QUOTE: \"stored_at plus ttl_seconds\"\n"
         "- second problem, no quote\nVERDICT — fine")
kept, dropped = tr.quote_gate(LISTY, ART)
assert (len(kept), dropped) == (1, 1), (kept, dropped)

print("OK")
