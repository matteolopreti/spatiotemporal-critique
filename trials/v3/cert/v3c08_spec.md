# Relay: Webhook Delivery Retry Policy

## Overview

Relay is the outbound webhook dispatcher for the platform. It delivers domain events to customer-registered HTTPS endpoints with at-least-once semantics. This document specifies the delivery attempt schedule, the classification of failures, idempotency guarantees, dead-letter handling, and endpoint auto-disable behavior. It does not cover event schemas or endpoint registration, which are specified separately.

Delivery is per-event and per-endpoint: each (event, endpoint) pair is an independent delivery job with its own retry state. Relay makes no ordering guarantee across events; consumers that need ordering must reconstruct it from the event timestamp and sequence fields in the payload.

## Delivery Attempts and Backoff

Each delivery job makes at most nine total attempts: one initial delivery plus up to eight retries. An attempt succeeds when the endpoint returns any 2xx status within the request timeout (10-second connect timeout, 30-second total request timeout). Any other outcome is a failure and is classified per the next section.

Retries follow a doubling backoff starting at one minute:

| Retry | Nominal delay after previous failure | Cumulative nominal delay |
|-------|--------------------------------------|--------------------------|
| 1     | 1 minute                             | 1 minute                 |
| 2     | 2 minutes                            | 3 minutes                |
| 3     | 4 minutes                            | 7 minutes                |
| 4     | 8 minutes                            | 15 minutes               |
| 5     | 16 minutes                           | 31 minutes               |
| 6     | 32 minutes                           | 63 minutes               |
| 7     | 64 minutes                           | 127 minutes              |
| 8     | 128 minutes                          | 255 minutes              |

The eight nominal delays total 255 minutes, so under the pure schedule a job exhausts its attempts no more than 4 hours 15 minutes of scheduled delay after the first failure. To spread thundering herds, each schedule-derived delay is jittered by drawing uniformly from [0.85 × d, d]; jitter shortens delays and never extends them, so 255 minutes remains the schedule's upper bound.

If a failure response carries a `Retry-After` header (seconds or HTTP-date), Relay honors it for the next retry whenever it exceeds the jittered scheduled delay, capped at 128 minutes — the largest delay in the schedule. Jitter is not applied to `Retry-After` overrides. Because every individual delay, scheduled or overridden, is at most 128 minutes, the absolute worst-case cumulative scheduled delay is 8 × 128 = 1,024 minutes (17 hours 4 minutes), and that bound is reached only if all eight retries are governed by overrides at the cap.

## Failure Classification

Retryable failures: connection errors, TLS handshake failures, request timeouts, HTTP 408, HTTP 429, and all 5xx responses. These consume a retry and follow the schedule above.

Non-retryable failures: every other 4xx response. The job is terminated immediately and the event moves to the dead-letter queue with the response status recorded as the reason.

Redirects (3xx) are never followed, as a defense against request forgery via attacker-controlled `Location` targets. A 3xx response is treated as a non-retryable failure.

## Idempotency

Every event carries a stable identifier, `event_id`, a UUIDv4 assigned once at enqueue time. All delivery attempts for a given (event, endpoint) job — including manual redeliveries from the dead-letter queue — send the same `X-Relay-Idempotency-Key` header containing that `event_id`, and the request body is byte-identical across attempts. Receivers MUST deduplicate on the key: on seeing a key they have already processed, they return 2xx without reprocessing. Under this contract, processing an event once or processing any number of duplicate deliveries produces the same receiver state, which is the idempotency guarantee Relay claims.

Per-attempt metadata that necessarily changes between attempts (attempt number, send timestamp) travels only in headers: `X-Relay-Attempt` (1 through 9) and `X-Relay-Timestamp`.

Each attempt is signed with HMAC-SHA256 over the string `<timestamp>.<event_id>.<raw body>` using the endpoint's shared secret; the signature is sent in `X-Relay-Signature`. Receivers MUST reject requests whose timestamp is more than five minutes from their clock, and the `event_id` deduplication above rejects replays of previously processed events even within that window.

## Dead-Letter Queue

An event enters the endpoint's dead-letter queue (DLQ) when its ninth attempt fails, when it hits a non-retryable failure, or when its endpoint is auto-disabled mid-flight. DLQ entries record the event, the terminal reason, the full attempt history, and the entry time.

DLQ retention is 14 days from entry. Within that window, operators and endpoint owners may trigger manual redelivery any number of times through the dashboard or API. A manual redelivery is a single attempt: on success the entry is removed from the DLQ; on failure it remains, and the 14-day retention clock is not reset. After 14 days, entries are purged and are no longer recoverable.

## Endpoint Auto-Disable

Relay auto-disables an endpoint when both conditions hold: every delivery attempt to it has failed for 72 consecutive hours, and at least 50 attempts were made in that window. Since a single job's retry cycle spans at most 1,024 minutes of scheduled delay — just over 17 hours — one stuck event cannot trip the threshold by itself; sustained failure across multiple events is required.

On auto-disable: jobs currently in their retry cycle for that endpoint move to the DLQ with reason `endpoint_disabled`, and newly enqueued events for the endpoint are written directly to the DLQ with the same reason, where the standard 14-day retention applies. The endpoint owner is notified by email at disable time and daily thereafter while events are accumulating.

Re-enabling is manual. After re-enable, new events flow normally, and DLQ entries within retention may be manually redelivered; Relay does not auto-replay the DLQ on re-enable, so owners control ordering and volume of the catch-up.

## Observability

Relay emits per-endpoint counters for attempts, successes, failures by class, DLQ entries, and DLQ redeliveries, plus a gauge for current DLQ depth. Every attempt is logged with `event_id`, attempt number, response status, and latency, retained for 30 days. Alerting on DLQ depth and auto-disable events is routed to the endpoint owner's configured channel.
