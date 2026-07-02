# Conveyor on-call runbook

Conveyor is our internal message-queue service. This runbook covers the alerts
you can be paged for, how to escalate, and the remediations that resolve the
common failure modes. It assumes you have `conveyorctl` installed and
production access through the ops bastion.

## Service overview

- **Cluster:** five brokers, `conveyor-broker-1` through `conveyor-broker-5`,
  each with a 4 TB data disk. Typical steady-state usage is about 2.8 TB per
  broker (70%).
- **Replication:** every partition has 3 replicas; writes require 2 in-sync
  replicas. With one broker down the cluster remains fully writable. With two
  brokers down, any partition that had two of its three replicas on the failed
  brokers rejects writes until a replica recovers; no acknowledged data is lost
  as long as one replica of each partition survives.
- **Defaults:** 72-hour retention; 32 partitions per topic; messages that fail
  delivery 5 times are routed to `<topic>.dlq`.
- **Dashboards:** `grafana.internal.example/conveyor` (cluster overview,
  per-broker, consumer groups).

## SLOs

- Publish availability: 99.95% per calendar month — an error budget of 21.6
  minutes per 30-day month.
- Publish latency: p99 at or under 250 ms. The latency alert threshold below is
  set exactly at this SLO figure.

## Alert reference

| Alert | Condition | Response |
|-------|-----------|----------|
| ConveyorPublishLatencyHigh | p99 publish latency > 250 ms for 10 min | Page, SEV-3 |
| ConveyorPublishErrors | Publish failure rate > 1% for 5 min | Page, SEV-2 |
| ConveyorBrokerDown | Broker unreachable > 2 min | Page, SEV-2 (SEV-1 if two or more brokers) |
| ConveyorUnderReplicated | Under-replicated partitions > 0 for 5 min | Page, SEV-2 |
| ConveyorConsumerLag | Group lag > 100,000 messages and rising for 15 min | Page, SEV-3 |
| ConveyorDiskWarn | Data disk > 75% used | Ticket (no page) |
| ConveyorDiskCritical | Data disk > 85% used | Page, SEV-2 |

## Escalation

Acknowledge pages within 5 minutes. If a page is unacknowledged, the paging
system re-pages the primary at 5 minutes, pages the secondary at 10 minutes,
and pages the engineering manager at 20 minutes. For SEV-1, primary and
secondary are paged simultaneously from the start. If you need more hands,
`conveyorctl oncall who` lists the current rotation; the escalation channel is
`#conveyor-ops`.

## Common remediations

### Consumer lag (ConveyorConsumerLag)

1. Check the group: `conveyorctl group describe <group>`. Confirm all members
   are connected and heartbeating.
2. If consumers are healthy but slow, scale the consumer deployment. Scaling
   beyond 32 replicas adds no throughput, since topics have 32 partitions and
   each partition is consumed by at most one member.
3. If lag is concentrated on a single partition, suspect a poison message.
   After 5 failed deliveries it will move to `<topic>.dlq` on its own; inspect
   it with `conveyorctl dlq peek <topic>`. If the handler is crashing before it
   can negatively acknowledge, fix or roll back the consumer first.

### Publish latency (ConveyorPublishLatencyHigh)

1. Check per-broker disk I/O on the dashboard; a single saturated broker
   usually shows up as one hot line.
2. Check whether a rebalance or a re-replication is in progress — both compete
   for disk and network.
3. If one broker is degraded, move leadership off it: `conveyorctl broker
   drain <id>`. A leadership drain completes in about 3 minutes and is safe
   during business hours.

### Broker down (ConveyorBrokerDown)

1. Try a restart: `conveyorctl broker restart <id>`.
2. If the node itself is unhealthy, replace it through the provisioning
   pipeline. A replacement broker re-replicates its ~2.8 TB share at the
   200 MB/s replication throttle, which takes roughly four hours.
3. During re-replication, ConveyorUnderReplicated fires continuously; that is
   expected. Silence that alert with a 5-hour window (long enough to cover the
   roughly four-hour copy) and note the silence in the incident channel.

### Disk usage (ConveyorDiskWarn / ConveyorDiskCritical)

1. First check for a runaway topic: `conveyorctl topics top` sorts by bytes
   stored and growth rate.
2. If growth is legitimate and disk is above 85%, the emergency lever is a
   retention cut from 72 hours to 48 hours, which reclaims roughly a third of
   stored bytes as segments older than 48 hours are deleted — usually within
   30 minutes. This requires sign-off from the owning team of any affected
   topic and an announcement in `#conveyor-ops`.
3. Restore retention to 72 hours once usage is back below the 75% warning
   threshold, and file a capacity ticket — the durable fix is adding a broker,
   not living with reduced retention.

### Rebalance storms

A consumer group that rebalances repeatedly (visible as sawtooth lag and
member churn in `conveyorctl group describe`) is usually caused by consumers
missing heartbeats under load or by a crash-looping pod. Check pod restarts
first. If members are merely slow, raise the group's session timeout from the
10-second default to 30 seconds and watch for the storm to settle.

## Maintenance

Rolling restarts happen on Tuesdays between 03:00 and 05:00 UTC. Restart one
broker at a time and wait for under-replicated partitions to return to zero
before moving on — typically 15–20 minutes per broker, so all five fit inside
the two-hour window even at the slow end. The maintenance tooling silences
broker-scoped alerts for the broker being restarted and holds a single silence
on ConveyorUnderReplicated for the duration of the window (restarts keep it
nonzero by design); publish-error, publish-latency, and consumer-lag alerts
stay live and should be treated as real.

## Handoff notes

At the end of a shift, summarize open silences, any retention overrides still
in place, and in-progress re-replications in `#conveyor-ops`. An override or
silence left behind without a note is the most common way the next on-call
gets surprised.
