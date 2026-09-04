# ADR 006: Asynchronous LLM Incident Reporting and Rate-Limiting Cooldown

## Status

Accepted

## Context

Underground mining operations require real-time, low-latency telemetry ingestion. ESP32 edge nodes and simulated telemetry agents transmit data packets to the `/api/telemetry` endpoint at high frequencies, typically every 1.0 to 1.5 seconds.

When an emergency or severe anomaly occurs (`final_risk == "CRITICAL"`), the system synthesizes tactical incident briefs and evacuation recommendations using a Large Language Model through the Google Gemini API.

However, integrating LLM services into a safety-critical ingestion loop introduces two major technical bottlenecks:

1. **Network and Inference Latency:** Generative AI API calls over external networks take between 1,500 ms and 4,000 ms to complete. Executing this call synchronously inside the HTTP `POST` route would block request processing, risk HTTP timeout errors such as `504 Gateway Timeout`, delay subsequent telemetry packets, and desynchronize real-time edge tracking.

2. **Quota Exhaustion and Denial of Service:** During an ongoing hazardous event—such as persistent toxic-gas dwell or entrapment—the edge unit continuously streams `CRITICAL` telemetry approximately every 1.5 seconds. Querying the LLM for every incoming payload would overwhelm external API rate limits, trigger `HTTP 429` responses, exhaust token quotas, incur unnecessary operational costs, and flood the operations center with duplicate incident reports.

## Decision

We implement **asynchronous execution with cooldown-based rate limiting** in `backend/main.py`.

```text
Incoming Telemetry (Every ~1.5 s)
               |
               v
      [Pessimistic Gating]
               |
      final_risk == CRITICAL?
          /             \
        YES              NO
         |                |
         |                +---> Return HTTP 200 TelemetryResponse (< 10 ms)
         v
    Cooldown Active?
(now - last_call < 30 s)
       /          \
     YES           NO
      |             |
      |             +---> Update last_llm_call_time = now
      |                         |
      |                         v
      |              Dispatch FastAPI BackgroundTasks
      |                  - background_llm_task()
      |                  - Non-blocking external API call
      |                         |
      +-------------------------+
               |
               v
Return HTTP 200 TelemetryResponse immediately (< 10 ms)
```

### 1. Decoupled Execution via `BackgroundTasks`

* Generative incident synthesis is offloaded through FastAPI's `BackgroundTasks` mechanism using `background_llm_task`.
* The HTTP endpoint returns a complete `TelemetryResponse`, including model inferences, rule scores, and local actuation triggers, to the edge client within `< 10 ms`.
* Sensor ingestion is therefore decoupled from the latency of the external generative AI service.

### 2. Stateful Cooldown Rate Limiter

* A global timestamp gate named `last_llm_call_time`, paired with the configurable threshold `LLM_COOLDOWN_SECONDS = 30.0`, governs the dispatch of generative requests.
* The cooldown condition is evaluated as:

$$
\Delta t = t_{\text{current}} - t_{\text{last LLM call}}
$$

$$
\text{Dispatch LLM} =
\begin{cases}
\text{True}, & \text{if } \texttt{final\_risk} = \texttt{CRITICAL}
\land \Delta t \ge 30 \text{ s} \\
\text{False}, & \text{otherwise}
\end{cases}
$$

* If a critical packet arrives less than 30 seconds after the previous incident-report request, the external API call is bypassed.
* The endpoint continues to expose the most recently generated report through `latest_incident_report["report"]` until the cooldown window expires.

Given a sustained critical event lasting $T$ seconds, the approximate maximum number of LLM requests is bounded by:

$$
N_{\text{LLM}}(T)
\le
\left\lceil
\frac{T}{30}
\right\rceil
$$

Without cooldown control, telemetry arriving every 1.5 seconds could generate approximately:

$$
N_{\text{unbounded}}(T)
\approx
\frac{T}{1.5}
$$

requests. The cooldown therefore reduces the theoretical request frequency from approximately 40 requests per minute to no more than 2 requests per minute during a continuous critical event.

### 3. Fault-Tolerant Cache

* Generated incident reports and their generation timestamps are cached in the in-memory `latest_incident_report` structure.
* Dashboard consumers accessing `/api/dashboard-data` retrieve the cached artifact without generating redundant upstream API requests.
* If the external LLM service is temporarily unavailable, telemetry ingestion and deterministic risk evaluation continue independently of report generation.

## Validation

### Telemetry Latency Validation

Endpoint response time must be measured with and without an active LLM dispatch. The telemetry response should remain independent of the external API's 1,500–4,000 ms inference latency.

The following latency metric should be recorded:

$$
L_{\text{telemetry}}
=
t_{\text{response sent}}
-
t_{\text{request received}}
$$

The accepted implementation target is:

$$
L_{\text{telemetry}} < 10 \text{ ms}
$$

under the defined local test environment and nominal system load.

### Cooldown Boundary Validation

A sequence of `CRITICAL` telemetry packets must be submitted at intervals shorter than 30 seconds. The test should confirm that:

* the first eligible critical packet dispatches an LLM task;
* subsequent critical packets inside the cooldown window do not dispatch additional tasks;
* a new task becomes eligible after the cooldown expires;
* non-critical telemetry never triggers LLM generation.

For two request timestamps $t_i$ and $t_j$, where $t_j > t_i$, a second dispatch is valid only when:

$$
t_j - t_i \ge \texttt{LLM\_COOLDOWN\_SECONDS}
$$

### Cache Validation

The `/api/dashboard-data` endpoint must be queried before, during, and after asynchronous report generation to confirm that:

* telemetry data remains available while report generation is pending;
* the previous report remains readable during the cooldown period;
* the cached report is updated after successful generation;
* dashboard reads do not trigger additional LLM calls.

### Failure-Isolation Validation

The external LLM client must be tested under timeout, quota-limit, and network-failure conditions. These failures must not:

* prevent `/api/telemetry` from returning its deterministic response;
* suppress local `action_required` signals;
* interrupt subsequent telemetry ingestion;
* overwrite a valid cached report with an incomplete result.

### Sustained-Critical-Event Validation

A continuous critical telemetry stream should be simulated for at least 60 seconds. With a 30-second cooldown, the number of dispatched LLM tasks must remain bounded to approximately two requests per minute rather than one request per telemetry packet.

## Consequences

### Positive

* **Deterministic Telemetry Ingestion:** Edge-to-backend communication does not wait for external LLM inference, preserving high-frequency telemetry ingestion during critical events.
* **Cost and Quota Protection:** Limiting report generation to once every 30 seconds substantially reduces redundant API consumption and lowers the risk of quota throttling.
* **Immediate Edge Actuation:** Edge devices receive an immediate response containing `action_required: true`, enabling local alarm activation without waiting for an LLM-generated report.
* **Failure Isolation:** External API failures do not interrupt deterministic risk evaluation or local safety decisions.
* **Reduced Report Duplication:** Persistent critical conditions do not flood the operations dashboard with nearly identical incident reports.

### Negative / Trade-offs

* **Initial Report Lag:** The first incident report becomes available on the dashboard only after asynchronous generation finishes.
* **Rapid Multi-Incident Resolution:** If two distinct sensor events occur within the same 30-second window, the second event does not generate a new LLM synthesis until the cooldown expires.
* **Process-Local State:** The global timestamp and in-memory report cache are local to the running application process. Deployments with multiple workers or replicas may enforce separate cooldown windows.
* **Non-Persistent Cache:** Restarting the backend clears `last_llm_call_time` and `latest_incident_report`.
* **Task Durability:** In-process background tasks may be lost if the application terminates before generation completes.
* **Fixed Cooldown Window:** A static 30-second interval may not suit every incident type or deployment environment.

## Operational Constraints

The LLM-generated report is advisory and must not participate in the immediate safety-decision path. The following outputs must remain fully deterministic and locally available:

* `final_risk`;
* `action_required`;
* local alarm triggers;
* evacuation-state transitions;
* telemetry acceptance and storage.

The deterministic risk engine and local actuation logic remain authoritative. LLM failure, timeout, quota exhaustion, or malformed output must not suppress or downgrade a critical alert.

## Future Considerations

For multi-worker or production deployment, the process-local cooldown and cache should be replaced with shared infrastructure, such as:

* Redis-backed distributed locking;
* a persistent incident-report cache;
* a durable task queue;
* incident identifiers for deduplication;
* event-aware cooldown invalidation;
* structured retry and exponential-backoff policies.

Any migration from process-local background tasks to distributed task execution should be documented in a new ADR that supersedes this decision.
