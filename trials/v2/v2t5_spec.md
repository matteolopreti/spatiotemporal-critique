# Migration Plan: Billing Monolith to Services

## Overview

The billing platform currently runs as a single deployable application responsible for subscription management, invoice generation, tax calculation, payment orchestration, credits, refunds, collections, customer balance tracking, reporting exports, and downstream accounting feeds. The migration goal is to reduce deployment risk, isolate high-change billing capabilities, and improve operational ownership without changing customer-facing billing behavior during the transition.

The target architecture separates billing into four services: Subscription Service, Invoice Service, Payment Service, and Ledger Service. The monolith will remain the system of record until each capability has been shadowed, validated, and promoted. All new services will expose versioned APIs, publish domain events through the existing message bus, and write operational telemetry to the centralized observability stack. The migration will use the strangler pattern: traffic is routed incrementally from the monolith to services through a billing facade, while legacy code paths remain available until cutover is complete.

Success criteria are functional parity, no increase in failed payment attempts, no material variance in invoice totals, reversible rollout at each phase, and a clean audit trail for every customer balance mutation. The migration will prioritize correctness over speed, particularly for ledger and invoice data, because these records are externally visible and subject to finance review.

## Phases

Phase A establishes the foundation. The team will introduce the billing facade inside the monolith boundary, define service contracts, add correlation IDs across billing workflows, and capture baseline metrics for invoice generation latency, payment authorization rate, retry success, and adjustment volume. No customer traffic will leave the monolith in this phase. The output is a stable routing layer, documented API contracts, and dashboards that compare old and new execution paths.

Phase B extracts invoice calculation. The Invoice Service will reproduce invoice draft generation, discounts, tax inputs, proration, and line-item ordering. It will run in shadow mode for two billing cycles, receiving the same inputs as the monolith and producing draft invoices that are compared field by field. Phase B cannot start until the canonical customer-balance event schema produced by Phase D has been accepted by finance operations and implemented by downstream consumers.

Phase C extracts payment orchestration. The Payment Service will own gateway token usage, payment intent creation, retry scheduling, authorization capture, and processor response normalization. During shadow mode, it will simulate processor calls using recorded gateway responses and compare decisions with the monolith. After approval, a small cohort of internal accounts will use live Payment Service execution while customer accounts remain on the monolith path.

Phase D extracts ledger posting and balance projection. The Ledger Service will own immutable ledger entries, balance views, credit application, refund posting, and accounting export events. It will initially consume monolith-generated billing events and produce a parallel ledger for reconciliation. Once variance remains within the finance-approved threshold for two complete accounting periods, the facade will route balance reads to the Ledger Service for internal users, then for customer-facing billing pages.

Each phase requires an architecture review, service readiness review, runbook approval, and production observability signoff before traffic promotion. Phase exits are based on measured parity rather than calendar dates.

## Rollback

Rollback is handled at the facade level whenever possible. The routing layer must support per-capability, per-cohort, and per-tenant routing so that any service can be removed from the live path without redeploying the monolith. Feature flags will be stored in the central configuration service, with emergency overrides available to the incident commander.

For Phase B, rollback means disabling invoice generation calls to the Invoice Service and returning to monolith draft generation. Shadow outputs may continue for diagnostics, but they must not write customer-visible invoice records. For Phase C, rollback means stopping live payment execution through the Payment Service and sending all payment attempts through the monolith gateway adapter. Any in-flight payment intents must be reconciled against gateway state before retrying.

For Phase D, rollback means restoring monolith balance reads and pausing Ledger Service projections. Because ledger entries are immutable, rollback must not delete service-created entries. Instead, the team will mark the projection as inactive, reconcile the entry stream, and resume shadow processing after correction.

Rollback decisions will be made using predefined thresholds: invoice total variance above tolerance, payment authorization degradation above tolerance, duplicate charge risk, ledger imbalance, processor incident, or missing audit events. Customer support and finance operations must be notified before any rollback that affects invoice presentation, payment retries, refunds, or account balances.

## Data Migration

Data migration will be performed in controlled batches, beginning with historical subscription records, followed by invoices, invoice line items, payments, refunds, credits, and ledger-relevant balance adjustments. The migration job will read from a consistent snapshot of the monolith database, transform records into service-owned schemas, and write them into service databases with source identifiers preserved.

The migration script is idempotent and safely re-runnable, so failed batches can be retried without creating duplicate records or changing previously migrated financial facts. Every migrated row will include source system, source table, source primary key, migration batch ID, and migration timestamp. Validation will compare record counts, invoice totals, customer balances, payment status distributions, and refund totals between the monolith and service stores.

Historical data will remain readable in the monolith for audit purposes until finance signs off on service reports for two accounting periods. Services will not mutate migrated historical invoices except through explicit adjustment records. This preserves the audit model and avoids rewriting customer-facing financial documents.

Batch execution will be limited to off-peak hours until performance is proven. The team will begin with internal test accounts, then migrate inactive customers, then active customers by billing cohort. Each batch will produce a reconciliation report reviewed by engineering and finance operations before the next batch starts.

## Cutover Checklist

Confirm all service dashboards include request rate, error rate, latency, queue lag, reconciliation variance, and business counters. Confirm alerts are routed to the owning team and that on-call engineers have access to service logs, traces, database metrics, and feature flag controls.

Confirm Phase D starts only after Phase B invoice extraction has completed production traffic promotion and finance has approved invoice parity reports.

Confirm the billing facade can route reads and writes independently for subscriptions, invoices, payments, and ledger balances. Confirm emergency rollback flags have been tested in production using internal accounts. Confirm customer support has updated runbooks for invoice disputes, failed payments, refunds, credits, and balance corrections.

Before final cutover, run the historical migration process for the selected cohort by inserting transformed records into each target service table, preserving source IDs for traceability but appending new rows for every source record processed during the batch. After migration, freeze billing mutations for the cohort, drain billing queues, execute final delta sync, validate reconciliation reports, and switch routing flags.

After cutover, monitor for one full billing cycle before removing monolith write paths. Decommissioning may begin only after successful reconciliation, support signoff, finance signoff, and completion of disaster recovery testing for all billing services.
