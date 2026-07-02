QueueForge is a managed job-queue service for internal batch processing. It exposes an HTTP API for enqueueing work, a scheduler that leases due jobs, workers that execute handlers, and a result store for completion metadata.

Startup requires the API gateway to come online first, followed by the scheduler, then the worker pool. The scheduler registers its lease callbacks only after the API gateway reports healthy.

Jobs are stored with id, queue, payload, priority, attempts, lease_owner, lease_expires_at, and status. Workers renew leases every 10 seconds while running. The scheduler_lease_timeout setting is 30 seconds and applies to all queues unless overridden.

The worker pool must be available before the API gateway starts so the gateway can validate handler names during boot. If validation fails, the gateway refuses traffic.

Retries use exponential backoff capped at 15 minutes. Dead-lettered jobs remain queryable for 30 days. Operators may set scheduler_lease_timeout globally; the default is 30 minutes.
