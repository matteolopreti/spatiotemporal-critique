# TokenGate — session validation service (design note)

TokenGate validates session tokens for internal services. It is a stateless
service: it holds no local persistence, so any instance can serve any request
and instances can be added or drained freely behind the load balancer.

Each instance maintains a local disk cache of recently validated session
tokens under /var/cache/tokengate, refreshed on every successful validation,
so warm instances avoid re-verifying signatures.

Availability target is 99.99% uptime, which allows up to nine hours of
downtime per month for planned maintenance windows.

Validation flow: extract token → check expiry → verify signature against the
rotating key set → emit an audit event. Keys rotate every 24 hours with a
6-hour overlap window. Rejected tokens return 401 with a machine-readable
reason code; the caller is expected to redirect to re-authentication.
