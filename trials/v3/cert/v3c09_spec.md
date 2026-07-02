# Data Retention and Deletion Pipeline

## Overview

This specification defines how the platform retains, expires, and destroys stored data. It covers the retention classes assigned to every dataset, the purge job that enforces expiry, the account-deletion pipeline, interactions with legal holds, and the audit trail that makes destruction provable. Every dataset in the data catalog MUST carry exactly one retention class; unclassified datasets fail catalog validation and cannot be deployed.

## Retention Classes

| Class | Contents                                             | Retention period        | Maximum query window |
|-------|------------------------------------------------------|-------------------------|----------------------|
| A     | Debug logs, traces, transient telemetry              | 30 days from write      | 30 days              |
| B     | Product analytics events                             | 180 days from write     | 180 days             |
| C     | Billing records, audit records, compliance evidence  | 7 years from creation   | 7 years              |
| D     | User-generated content                               | Life of the account     | Application-defined  |

The query window for each class equals its retention period: no dashboard, report, or API may be configured with a lookback longer than the retention of the class it reads, so a query can never silently span purged data. Catalog validation enforces this at deploy time.

Class C retention is a legal requirement and is not shortened by account deletion; this is disclosed in the privacy notice. Class D data has no fixed expiry while the account is active and is destroyed through the account-deletion pipeline below.

## Purge Schedule

The purge job runs daily at 02:00 UTC. Each run scans catalog-registered datasets for rows whose retention expired on or before the run date, excludes anything under legal hold, and hard-deletes the remainder from primary stores. The service-level objective is that expired data is destroyed within 72 hours of expiry; the daily cadence normally achieves this within 24 hours, leaving headroom for a failed run and its rerun inside the objective.

Deletion proceeds through five ordered stages, each gated on the previous stage completing:

1. Tombstone: write a deletion marker keyed by record identifier.
2. Primary purge: hard-delete from primary datastores.
3. Derived purge: delete from search indexes, caches, and read replicas.
4. Verification: run a zero-hit scan for a sample of tombstoned keys across all stores from stages 2 and 3.
5. Audit append: write the run's audit record (see Audit Trail).

Tombstones are retained for 90 days. Encrypted backups are retained for 35 days and are not queryable; deleted data can therefore persist inside backups for up to 35 days after purge. Any restore procedure MUST re-apply live tombstones before the restored store serves traffic. Because tombstone retention exceeds backup retention by 55 days, every backup that is still restorable is guaranteed to overlap the tombstones for data purged during its lifetime, so a restore can never resurrect purged records.

## Account Deletion Pipeline

An account-deletion request starts a 14-day recovery window during which the account is deactivated but fully restorable and no data is destroyed. If the user does not cancel within the window, the pipeline becomes irreversible and MUST complete within 30 days of the window's end. The user-facing commitment is therefore: deletion completes no later than 44 days after the request (14-day window plus 30-day completion), excluding records under legal hold, as disclosed at request time.

Within the 30-day completion period: Class D content is hard-deleted through the five-stage process above; Class B events referencing the account are pseudonymized by replacing the user identifier with an irreversible random token, after which they age out on their normal 180-day clock; Class C records are untouched and retain their 7-year clock. Class A data needs no special handling — the account is deactivated at request time, so no new Class A records referencing it are written after day 0, and existing records expire on their 30-day clock well inside the 44-day horizon.

Counting backup retention, every copy of a deleted account's Class D content — primaries, derived stores, and backups — is destroyed no later than 79 days after the request (44-day completion plus 35-day backup retention).

## Legal Holds

A legal hold names specific custodians or record sets and suspends destruction for exactly the records it names. The purge job and the account-deletion pipeline both consult the hold registry and skip held records; everything not named by a hold proceeds on its normal schedule. Holds never extend a retention period for non-held records and never shorten one for anything.

When a hold is released, records whose retention has already expired are picked up by the next daily purge run, and the 72-hour destruction objective for those records is measured from the release time, not from the original expiry. If an account-deletion request arrives while some of the account's records are held, the pipeline deletes all non-held data on the normal 44-day schedule, queues the held records, and destroys them within 72 hours of hold release.

Hold creation, modification, and release each require a named legal approver and are themselves recorded in the audit trail.

## Audit Trail

Every purge run, account-deletion completion, and hold action appends one audit record capturing: the acting principal (or `system:purge` for scheduled runs), the retention class, the dataset, the count of records destroyed, the covered date range, and the run timestamp. The audit store is append-only for the life of each record: no API exists to modify or delete audit records, and destruction occurs only through the scheduled purge when a record's own 7-year retention expires.

Audit records are Class C and expire on the standard 7-year clock. When a purge run destroys expired audit records, that run appends its own one-line summary record (count and date range destroyed), which starts a fresh 7-year clock. The chain of summaries therefore persists indefinitely at one record per run; this is intentional, keeps volume negligible, and preserves an unbroken provenance chain showing that destruction itself was audited.

Quarterly, the compliance team samples audit records against catalog retention rules and files the reconciliation report as Class C compliance evidence.
