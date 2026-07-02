**Incident Postmortem: Payment Gateway API Latency and Failure (October 12, 2023)**

**Summary**
On October 12, 2023, the Payment Gateway API experienced a significant degradation in service, resulting in increased latency and a high rate of 5xx errors for customers attempting to process transactions. The incident began at approximately 13:40 UTC and lasted for 90 minutes before full service was restored. During this window, users reported failures during the checkout flow, particularly affecting high-volume merchants. The issue was identified as a resource exhaustion problem within our connection pooling logic, which prevented the application from establishing timely connections to the underlying database.

**Timeline**
*   13:40 UTC - First customer reports of transaction failures and "Gateway Timeout" errors are received by the Support team.
*   13:55 UTC - Monitoring systems trigger alerts for elevated 5xx error rates on the `/v1/charge` endpoint.
*   14:05 UTC - SRE team initiates a manual configuration change to the load balancer to reroute traffic to a secondary cluster (Triggering Event).
*   14:10 UTC - Engineering begins investigation into database connection pool saturation.
*   14:20 UTC - Internal dashboard shows a spike in `ConnectionTimeoutExceptions`.
*   14:30 UTC - Deployment of the `AuthService` update v2.1.0 is completed successfully.
*   14:45 UTC - Engineering identifies a configuration error in the connection pooler settings.
*   15:10 UTC - Configuration fix is deployed to production.
*   15:30 UTC - Monitoring confirms that 5xx error rates have returned to baseline levels.

**Root Cause**
The primary driver of this incident was the deployment of the `AuthService` update v2.1.0 at 14:30 UTC, which caused the initial spike in transaction failures by saturating the connection pool and preventing valid requests from being processed. This occurred because the new configuration parameters for the connection pool were set too low for our peak traffic volume, leading to a "thundering herd" effect where requests queued indefinitely until they timed out.

**Impact**
The incident affected approximately 15% of all transaction attempts during the reported window. We estimate that over 4,200 transactions failed to complete, primarily impacting users in the EMEA and North America regions. While no data breach occurred, the loss of availability resulted in a significant drop in successful conversions for our retail partners. Our internal systems remained operational, but the latency propagated to downstream microservices, causing secondary delays in order fulfillment notifications.

**Action Items**
*   **Immediate:** Roll back the `AuthService` configuration to the previous stable version and verify connection pool stability (Completed).
*   **Short-term:** Implement more granular alerting for connection pool saturation levels, specifically targeting "Wait Time" metrics rather than just "Active Connection Count."
*   **Medium-term:** Conduct a comprehensive audit of all service configurations to ensure that production values are aligned with current peak traffic projections.
*   **Long-term:** Develop an automated load testing suite that simulates 2x our current peak volume to identify potential bottlenecks in the connection pooling logic before they reach production.
