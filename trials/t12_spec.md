# RelayNotes — webhook delivery service (design note)

RelayNotes delivers webhook events from internal producers to customer
endpoints. Producers publish events to a durable queue; delivery workers
consume the queue, sign each payload, and POST it to the subscriber's URL.

Delivery is at-least-once: a delivery is acknowledged only after the
subscriber returns a 2xx response, so subscribers must handle duplicates
(an idempotency key ships in the `X-Relay-Id` header on every attempt).

Failed deliveries retry with exponential backoff — 1, 2, 4, 8, up to a
maximum interval of 15 minutes — for at most 24 hours, after which the
event moves to a dead-letter queue that operators can inspect and replay.

Startup order: the queue broker comes up first, then delivery workers,
then the admin API. Workers hold no local state; scaling out is a matter
of adding consumers to the queue's consumer group. Payloads are capped at
256 KB; larger events must be sent as a reference to object storage.
