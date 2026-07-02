**Technical Design Document: Project AetherLog (Distributed Log Ingestion Pipeline)**

**1. Document Purpose & System Goals**
This document outlines the architectural design for Project AetherLog, a unified, high-throughput log ingestion and analysis pipeline. The system is designed to aggregate, parse, index, and store application and system logs generated across our global Kubernetes clusters. 

The primary business and technical goals of AetherLog are:
*   **Low-Latency Ingestion:** Provide near real-time log availability (under 3 seconds from emission to index).
*   **Scalability:** Horizontally scale to handle regional traffic spikes without dropping log messages or introducing backpressure.
*   **Cost Efficiency:** Implement tiered storage to minimize the cost of long-term log retention.
*   **High Availability:** Ensure the ingestion endpoint remains highly resilient to regional cloud outages and network partitions.

**2. System Architecture**
The AetherLog pipeline utilizes a decoupled, event-driven architecture consisting of four primary layers: Collection, Buffering, Processing, and Storage.

*   **Collection Layer:** Lightweight daemonsets (using Vector) run on each Kubernetes node, scraping container stdout/stderr streams, parsing basic container runtime metadata, and forwarding them via TLS to the buffering layer. The agents are configured with file-based disk buffers to prevent data loss in the event of transient network partitions between the edge nodes and the ingestion load balancers.
*   **Buffering Layer (Apache Kafka):** A multi-AZ Kafka cluster acts as the primary ingestion buffer, deployed across three availability zones in our primary cloud region. This setup decouples the collection layer from downstream processing bottlenecks, provides up to 24 hours of replayable log history, and absorbs sudden traffic spikes during application deployments or cascading failures.
*   **Processing Layer (Aether-Consumer):** A custom Go-based service runs as a deployment in our core region, scaling dynamically based on consumer group lag. These consumers pull raw logs from Kafka, parse common formats (JSON, Logfmt), enrich them with Kubernetes metadata (namespace, pod name, node), and route them to their respective destinations. The consumer application also handles schema enforcement, dropping malformed payloads to a dead-letter queue (DLQ) for manual inspection.
*   **Storage Layer:** To support compliance audits, the system allows users to query historical cold storage logs up to 90 days old using an on-demand Athena-based query interface. For active troubleshooting, indexed logs are written to an OpenSearch cluster.

**3. Capacity Planning**
To ensure the infrastructure is adequately provisioned, we modeled our resource requirements based on current production metrics and a 2x growth multiplier for peak events.

We anticipate a peak ingestion rate of 50,000 log events per second across all production clusters. Assuming an average uncompressed log event size of 2 KB, the pipeline must be provisioned to handle a peak throughput of 100 GB per second at the ingestion tier.

Based on these metrics, the Kafka buffer requires a minimum of 15 partitions per topic to distribute the write load evenly across brokers without exceeding the disk I/O limits of our standard EBS volumes. The OpenSearch cluster will require 12 data nodes, each provisioned with 1.5 TB of NVMe storage, to handle the daily indexing volume while maintaining a healthy 30% storage headroom for index merges and replication. This sizing ensures we can accommodate sustained peak traffic without experiencing backpressure at the collection layer.

**4. Service Level Objectives (SLOs)**
The AetherLog platform commits to strict reliability and performance targets to support downstream engineering teams who rely on logs for operational visibility.

*   **Ingestion Latency:** 95% of log messages must be searchable in the OpenSearch dashboard within 3.0 seconds of reaching the ingestion gateway.
*   **Data Loss:** Zero unrecoverable log messages once acknowledged by the Kafka buffering layer.
*   **Endpoint Availability:** The ingestion pipeline target availability is set to 99.9% over any rolling 30-day window, which translates to a maximum allowable downtime budget of 4.32 minutes per month for critical ingestion endpoints.

**5. Data Retention & Archival**
To balance operational utility with cloud infrastructure costs, AetherLog implements a strict tiered retention policy.

*   **Hot Tier (OpenSearch):** Logs remain fully indexed and searchable in OpenSearch for 7 days. This tier is optimized for rapid querying and active incident response.
*   **Warm Tier (OpenSearch UltraWarm):** After 7 days, indices are migrated to warm nodes, where they remain searchable with slightly higher latency for an additional 14 days.
*   **Cold Tier (Amazon S3):** All logs in the cold storage tier (S3) are governed by an automated lifecycle policy that permanently purges objects exactly 30 days after ingestion.

By enforcing these automated transitions, we ensure that storage costs scale linearly with active usage while maintaining a predictable, bounded footprint for historical data.
