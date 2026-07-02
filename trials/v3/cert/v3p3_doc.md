# Capacity Plan — Orders Platform, FY27 H1

**Status:** Draft for review · **Owner:** Platform Engineering · **Planning window:** July 2026 – June 2027

## 1. Purpose and scope

This document sizes the orders platform for the next twelve months. It covers the API gateway, the application tier, the PostgreSQL primary and replicas, the Redis cache tier, and primary storage. The analytics warehouse and the ML feature store are budgeted separately and are out of scope here.

## 2. Method and assumptions

We size against the weekly peak, not the daily average: the platform must hold its latency SLO at the worst sustained hour, and everything below that follows. Utilization figures are one-minute samples from node metrics, taken at the weekly peak window and averaged over the last four weeks. Headroom means 100% minus peak utilization for the tier. We assume request handling scales close to linearly with node count for the stateless tiers; the database primary is a single writer and scales only vertically, so its numbers deserve the closest reading.

## 3. Current load profile

Peak traffic reaches 4,200 requests per second in the weekday 19:00–21:00 UTC window, against a daily average of 1,800 req/s. p99 latency at peak is 210 ms against a 300 ms SLO. Writes are 31% of peak requests, concentrated on the checkout and inventory endpoints. Batch reconciliation runs at 03:00 UTC and does not overlap the peak window.

## 4. Peak utilization

| Tier | Nodes | Peak utilization |
|---|---|---|
| API gateway | 4 | 44% CPU |
| Application | 12 | 58% CPU |
| Database primary | 1 | 78% CPU |
| Database replicas | 2 | 46% CPU |
| Cache (Redis) | 3 | 41% memory |

Replica lag stays under 400 ms at peak, and connection pools sit at 60% of their configured maximum. Cache hit rate holds at 96%; the miss path adds one replica read per request.

## 5. Growth outlook

Request volume has grown 10% month-over-month for six consecutive months, driven by the EU rollout and the partner API launch. We assume the same rate holds through the planning window. Put differently, at this rate peak volume doubles roughly every four months, so the plan must absorb two full doublings before the window closes.

Projected peak request rates at the assumed rate:

| Horizon | Projected peak req/s |
|---|---|
| Today | 4,200 |
| +3 months | 5,590 |
| +6 months | 7,440 |
| +12 months | 13,180 |

The partner API adds burst risk on top of the trend line: partner launches have historically produced short spikes of 20–30% above the weekly peak. The gateway absorbs these today; we treat them as a load-test scenario rather than a sizing input.

## 6. Storage

Primary storage stands at 2.1 TB, with ingest currently adding about 120 GB per month. If monthly ingest tracks request growth, the twelve monthly increments sum to roughly 2.6 TB, taking primary storage to about 4.7 TB by the end of the window. We will raise the provisioned volume to 6 TB in Q3 so that expansion never lands in the critical path. Index bloat is handled by the existing weekly maintenance job and is not a sizing factor at this scale.

## 7. Headroom assessment

Every tier retains at least 40% headroom at current peak, so no hardware changes are required this quarter. The fleet as measured absorbs the near-term ramp, and procurement can be deferred to the +6-month review, where we will re-baseline utilization against the Section 5 projections and size the second half of the window with fresher data.

## 8. Risks

- **Burst above trend.** A partner launch coinciding with the weekly peak compresses gateway headroom; mitigations are the existing rate limiter and the load-test scenario noted in Section 5.
- **Cache node loss.** Losing one of three Redis nodes at peak pushes the survivors toward their memory ceiling. The fleet tolerates a single loss today; we will rehearse the failover quarterly.
- **Replica promotion.** A primary failover during the peak window briefly doubles read pressure on the surviving replica while the pool rebalances. Runbook DR-12 covers the sequence.
- **Forecast error.** If observed peaks run 15% above the projection for two consecutive weeks, the +6-month review moves up immediately rather than waiting for the calendar.

## 9. Actions

1. Raise primary storage provisioning to 6 TB (Q3).
2. Add one Redis node when cache memory passes 65% at peak.
3. Keep the load-test suite pinned to the Section 5 projection table.
4. Re-baseline all tiers at the +6-month review.
