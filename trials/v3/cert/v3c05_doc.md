# Post-incident review: INC-2026-0147 — checkout-api connection-pool exhaustion

**Status:** Resolved. **Severity:** SEV-1. **Date:** Tuesday, 2026-05-12 (all times UTC).
**User-facing impact:** 50 minutes (10:02–10:52). **Author:** Payments platform team.

## Summary

A refactor shipped in checkout-api v2026.5.3 caused each checkout request to hold
two database connections from the same per-pod pool at once. When morning traffic
ramped past its usual level shortly after 10:00, connection waits became
self-reinforcing and all twelve pods exhausted their pools. Checkout requests
failed with HTTP 503 until we rolled back to v2026.5.2. No orders were lost or
partially written.

## Impact

- Elevated latency on /orders from 10:02; elevated error rates from 10:18 to
  10:52 (34 minutes).
- Traffic averaged 9,000 requests/minute during the error window (peak: 9,600
  at 10:30): of roughly 306,000 checkout attempts, 45,900 (15%) failed with
  HTTP 503. The error rate peaked at 31% at 10:38.
- No data loss or corruption. Failed requests either never obtained a first
  connection or had their open transaction rolled back when the second
  acquisition timed out. The nightly reconciliation job on 2026-05-12 confirmed
  zero partial orders.
- The database itself was healthy throughout: application connections are capped
  at 600 (12 pods × 50), well under the server's max_connections of 1,000, and
  database CPU peaked at 18%.

## Timeline (UTC, 2026-05-12)

- **09:14** — Canary pod (1 of 12) begins running v2026.5.3.
- **09:32** — Canary metrics reviewed; promotion approved. All metrics normal.
- **09:41** — Rolling deploy completes; all 12 pods on v2026.5.3.
- **10:00** — A marketing promotion email goes out. Checkout traffic climbs from
  roughly 6,500 to 9,100 requests/minute (+40%) over the next five minutes.
- **10:02** — p99 latency on /orders begins breaching the 1,200 ms alert
  threshold.
- **10:07** — Alert fires after five consecutive minutes over threshold; page
  sent. Observed p99: 1,450 ms.
- **10:12** — Primary on-call acknowledges.
- **10:18** — 5xx rate crosses 5%. SEV-2 declared.
- **10:26** — 5xx rate reaches 22%. Escalated to SEV-1; incident commander
  assigned.
- **10:33** — Pool dashboards show all 12 pods at 50/50 connections with queued
  waiters; connection-acquisition timeouts correlate one-to-one with 503s.
- **10:38** — Diff review of v2026.5.3 identifies the fraud-scoring change as
  the only code path touching connection handling.
- **10:41** — Rollback to v2026.5.2 initiated.
- **10:52** — Rollback complete on all 12 pods (11 minutes). 5xx rate below 1%.
- **11:00** — Error rate back at the 0.2% baseline; latency normal.
- **11:15** — Incident closed after fifteen minutes of stable metrics.

## Root cause

v2026.5.3 refactored fraud scoring into a helper, `recordFraudScore`, which
opened its own transaction — checking out a second connection from the same
per-pod pool (size 50, acquisition timeout 5 seconds) while the request's
primary connection was still held. Every checkout therefore needed two
concurrent connections.

At moderate traffic this only doubled brief connection usage. But the failure
mode is concurrency-dependent: once enough requests per pod held a first
connection while waiting for a second, waiting itself inflated connection hold
times, which increased concurrency further. After the 10:00 traffic ramp, each
pod was receiving about 12.5 requests/second (9,000/min across 12 pods); with
waits stretching toward the 5-second acquisition timeout, concurrent demand per
pod exceeded 60 connections against a pool of 50. Within minutes every pool sat
at 50/50, most holders were themselves waiters, and throughput collapsed.
Requests that timed out surfaced as 503s.

## Why the canary did not catch it

The canary soaked from 09:14 to 09:32, when traffic was around 6,300
requests/minute — well below the level at which two-connection demand
saturates a pool. The defect produces no signal at low concurrency: canary
latency, error rate, and connection counts all looked normal, and the promotion
decision was reasonable given the data available.

## What went well

- The latency alert fired five minutes after sustained breach began (10:02 →
  10:07), and the page was acknowledged within five minutes.
- Rollback tooling worked first try and completed in 11 minutes.
- Reconciliation confirmed order integrity the same day.

## What went poorly

- 34 minutes elapsed between the first page (10:07) and the rollback decision
  (10:41). We had no alert on connection-pool saturation, so diagnosis ran
  through dashboards and a manual diff review.
- The canary policy measures a fixed 18-minute soak regardless of traffic
  conditions, so a concurrency-dependent defect could pass cleanly.

## Where we got lucky

- The traffic ramp arrived mid-morning with the full team online, not during
  the overnight on-call window.
- The rolled-back release required no schema changes, so rollback was a pure
  binary swap.

## Error-budget accounting

The checkout SLO is 99.9% monthly availability, defined per minute: a minute
counts against the budget when the 5xx rate exceeds 5%. That gives a budget of
43.2 minutes per 30-day month. This incident consumed 34 minutes — 78.7% of
May's budget — leaving 9.2 minutes for the remainder of the month. Feature
releases to checkout-api continue under normal policy but will freeze if the
remaining budget drops below 5 minutes.

## Action items

| ID | Action | Owner | Due |
|----|--------|-------|-----|
| AI-1 | Alert on pool saturation: page when connection-acquisition wait p95 exceeds 500 ms for 3 minutes | Platform | 2026-05-19 |
| AI-2 | Refactor `recordFraudScore` to reuse the request's connection; add an integration test that fails if any code path acquires two pool connections in one request | Payments | 2026-05-26 |
| AI-3 | Canary policy: canaries must either span the weekday morning peak (09:30–11:00) or receive synthetic load at 1.5× recent peak | Release Eng | 2026-06-09 |
| AI-4 | Staging load test at 14,400 requests/minute (1.5× the May peak of 9,600) before each checkout-api release | Performance | 2026-06-09 |
| AI-5 | Cut rolling-rollback time from 11 minutes to under 10 by raising max-unavailable from 1 pod to 3 during rollbacks | Platform | 2026-05-26 |
