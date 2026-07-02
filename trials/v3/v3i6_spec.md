## overview

This specification defines blue-green promotion and rollback for the fictional **HelioMesh Service Platform**, covering stateless application services behind **Astra Edge Router**. The goal is to promote a release from the idle production color to the active production color with bounded customer impact, measurable gates, and a deterministic rollback path.

A production color is a complete, independently deployable runtime stack: compute, service mesh sidecars, configuration, secrets, caches, and outbound integration clients. At any time, exactly one color is the **primary color** receiving normal production traffic, and the other is the **candidate color** receiving either no traffic or a controlled percentage of production traffic.

## environments and traffic model

HelioMesh uses four environments:

- **dev**: continuous deployment from mainline builds; no production data.
- **staging**: production-like dependencies with anonymized data; validates release candidates.
- **prod-blue**: one complete production color.
- **prod-green**: one complete production color.

Astra Edge Router owns external traffic distribution. Traffic weights are set in whole percentages and must always sum to exactly **100%** between prod-blue and prod-green. Internal health checks, synthetic probes, and operator traffic do not count toward customer traffic percentages.

The standard production promotion path is:

- **0% candidate / 100% primary**
- **1% candidate / 99% primary**
- **10% candidate / 90% primary**
- **50% candidate / 50% primary**
- **100% candidate / 0% primary**

The previous primary remains fully provisioned and rollback-ready for **60 minutes** after the candidate reaches 100%.

## promotion criteria

A release may enter production promotion only after all staging gates pass:

- Unit, integration, and contract test suites pass with **0 failed required tests**.
- Staging deployment is stable for **30 continuous minutes**.
- `/livez` and `/readyz` return HTTP 200 for **100%** of staging probes during the final **10 minutes**.
- Synthetic checkout, login, and account-read probes each succeed at **99.9% or higher** over the final **10 minutes**.
- No unresolved Sev-1 or Sev-2 incident is open for HelioMesh.

At every production traffic gate, the candidate must meet all thresholds for the full observation window before advancing:

- Candidate HTTP 5xx rate is **0.20% or lower**, measured as no more than **20 failed requests per 10,000 candidate requests**.
- Candidate HTTP 4xx rate must not exceed the primary color by more than **0.50 percentage points**.
- Candidate p95 latency is **250 ms or lower**.
- Candidate p99 latency is **700 ms or lower**.
- Candidate CPU utilization is **70% or lower** for each service pool.
- Candidate memory utilization is **75% or lower** for each service pool.
- Queue lag for asynchronous workers is **60 seconds or lower**.
- Error-budget burn rate is less than **2.0x** over the active gate window.

A gate with fewer than **10,000 candidate requests** must be extended until it has at least **10,000 candidate requests** or has observed traffic for **30 minutes**, whichever happens first.

## promotion procedure step by step

1. Confirm the current primary color and candidate color in the deployment record. If prod-blue is primary, prod-green is candidate; if prod-green is primary, prod-blue is candidate.

2. Deploy the release artifact to the candidate color with customer traffic at **0%**. Do not modify the primary color.

3. Run database preflight checks. Confirm all required expand-phase schema changes are present, all migrations are marked complete, and no contract-phase migration is included in the release.

4. Run candidate smoke tests using operator-routed traffic. Smoke tests must include authentication, read path, write path, cache lookup, background job enqueue, and outbound notification delivery.

5. Shift traffic to **1% candidate / 99% primary**. Observe for **10 minutes**. Advance only if all production gate thresholds pass.

6. Shift traffic to **10% candidate / 90% primary**. Observe for **20 minutes**. Advance only if all production gate thresholds pass.

7. Shift traffic to **50% candidate / 50% primary**. Observe for **30 minutes**. Advance only if all production gate thresholds pass.

8. Shift traffic to **100% candidate / 0% primary**. Observe for **30 minutes**. If all thresholds pass, mark the candidate as the new primary color.

9. Keep the previous primary color deployed, healthy, and rollback-ready for **60 minutes** after the 100% shift. After 60 minutes with no rollback trigger, scale the previous primary to standby capacity.

The minimum production observation time before the 100% shift is **60 minutes**: 10 minutes at 1%, 20 minutes at 10%, and 30 minutes at 50%.

## rollback triggers and procedure

Rollback is required when any of the following occurs:

- Candidate HTTP 5xx rate exceeds **0.20%** for **2 consecutive minutes**.
- Candidate p95 latency exceeds **250 ms** for **2 consecutive minutes**.
- Candidate p99 latency exceeds **700 ms** for **2 consecutive minutes**.
- Candidate queue lag exceeds **60 seconds** for **2 consecutive minutes**.
- Candidate CPU exceeds **70%** or memory exceeds **75%** for **5 consecutive minutes**.
- Any customer-impacting Sev-1 incident is declared during promotion.
- Any irreversible data corruption is suspected.

Rollback procedure:

1. Freeze promotion immediately. Do not advance traffic while investigation is active.

2. If candidate traffic is below 100%, return Astra Edge Router to **0% candidate / 100% primary**.

3. If candidate traffic is already at 100% and the previous primary is still within the 60-minute rollback-ready window, route traffic back to **100% previous primary / 0% candidate**.

4. Disable candidate background workers before disabling candidate web traffic only if duplicate asynchronous processing is observed. Otherwise, shift web traffic first, then stop candidate workers.

5. Confirm primary health for **10 minutes** using the same production thresholds.

6. Open a rollback incident record with release ID, failed gate, trigger metric, start time, rollback time, and customer impact.

## database migration compatibility rules

HelioMesh uses expand-contract migrations. Every production release must be compatible with both colors running concurrently.

Expand rules:

- Additive schema changes are allowed: new nullable columns, new tables, new indexes, and new enum values.
- Application code must tolerate both old and new schema fields.
- Writes to new fields may begin only after the expand migration is complete in production.
- Reads from new fields must include fallback behavior until the contract release is complete.

Contract rules:

- Destructive changes are forbidden during blue-green promotion.
- Dropping columns, renaming columns, removing enum values, and changing field semantics require a separate contract release.
- A contract release may run only after the previous primary color has been retired and no supported application version depends on the old schema.
- Contract migrations must be reversible or have a documented restore procedure tested in staging.

## observability requirements

Each color must emit metrics with `service`, `release_id`, `color`, `region`, and `route` labels. Dashboards must display candidate and primary side by side for request rate, 4xx rate, 5xx rate, p95 latency, p99 latency, CPU, memory, queue lag, and dependency errors.

Logs must include `request_id`, `release_id`, and `color`. Distributed traces must sample at **10%** during promotion and return to the service default after the previous primary leaves the rollback-ready window.

Alerts must evaluate candidate-specific metrics independently from aggregate production metrics. Aggregate metrics alone are not sufficient for promotion or rollback decisions.

## open questions

- Should high-risk services require an additional **25% candidate / 75% primary** gate between 10% and 50%?
- Should rollback-ready retention remain **60 minutes** for all services, or vary by service recovery time?
- Which services require regional promotion instead of global traffic shifting?
- Should synthetic probe success remain at **99.9%**, or match each service’s formal SLO?
- What is the maximum acceptable standby cost for keeping the previous primary fully provisioned?
