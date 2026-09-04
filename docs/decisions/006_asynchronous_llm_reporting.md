# ADR 006: Asynchronous LLM Incident Reporting and Rate-Limiting Cooldown

## Status

Accepted

## Context

Underground mining operations require responsive telemetry ingestion. ESP32 edge nodes and simulated telemetry agents transmit data packets to the `/api/telemetry` endpoint at regular intervals, typically every 1.0 to 1.5 seconds.

When an emergency or severe anomaly occurs (`final_risk == "CRITICAL"`), the system generates tactical incident briefs and evacuation recommendations using a Large Language Model through the Groq API.

Integrating an external LLM service directly into a safety-related telemetry loop introduces two major technical risks:

1. **Network and inference latency:** External generative AI requests may take several seconds depending on network conditions, provider load, and model response time. Executing this request synchronously inside the HTTP `POST` route would block telemetry processing, increase the risk of HTTP timeouts, delay subsequent packets, and reduce system responsiveness.

2. **Quota exhaustion and repeated requests:** During a sustained hazardous condition, the edge unit may continuously transmit `CRITICAL` telemetry. Sending an LLM request for every packet could exceed provider rate limits, trigger `HTTP 429` responses, consume unnecessary tokens, and produce duplicate incident reports.

## Decision

We implement **background execution with cooldown-based rate limiting** in `backend/main.py`.

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
         |                +---> Return TelemetryResponse
         v
    Cooldown Active?
(now - last_call < 30 s)
       /          \
     YES           NO
      |             |
      |             +---> Update last_llm_call_time
      |                         |
      |                         v
      |              Dispatch FastAPI BackgroundTask
      |                  - background_llm_task()
      |                  - External Groq API call
      |                         |
      +-------------------------+
               |
               v
Return TelemetryResponse without waiting for the LLM
```

### 1. Decoupled Execution via `BackgroundTasks`

- Incident-report generation is dispatched through FastAPI's `BackgroundTasks` mechanism using `background_llm_task`.
- The endpoint returns a `TelemetryResponse` containing model results, the deterministic risk score, and the local actuation signal without waiting for the external Groq request to finish.
- Telemetry ingestion is therefore decoupled from external LLM network and inference latency.
- The initial prototype performance target is to keep local telemetry-processing latency below `10 ms` under nominal development conditions, excluding network transport and background LLM execution.
- This latency target must be verified through repeatable benchmark measurements before it can be reported as an achieved result.

### 2. Stateful Cooldown Rate Limiter

A global timestamp named `last_llm_call_time`, paired with the configured value `LLM_COOLDOWN_SECONDS = 30.0`, controls the dispatch of new incident-report requests.

The cooldown condition is:

$$
\Delta t =
t_{\text{current}} -
t_{\text{last LLM call}}
$$

$$
\text{Dispatch LLM} =
\begin{cases}
\text{True},
& \text{if } \texttt{final\_risk} = \texttt{CRITICAL}
\land \Delta t \ge 30\text{ s} \\
\text{False},
& \text{otherwise}
\end{cases}
$$

If a critical packet arrives less than 30 seconds after the previous eligible request, the external API call is skipped.

The endpoint continues to expose the most recently generated report through `latest_incident_report["report"]` while the cooldown remains active.

For a sustained critical event lasting $T$ seconds, the approximate maximum number of dispatched LLM requests is:

$$
N_{\text{LLM}}(T)
\le
\left\lceil
\frac{T}{30}
\right\rceil
$$

Without cooldown protection, telemetry arriving every 1.5 seconds could theoretically produce:

$$
N_{\text{unbounded}}(T)
\approx
\frac{T}{1.5}
$$

LLM requests.

The cooldown therefore limits the theoretical request frequency to approximately two requests per minute during a continuous critical condition.

### 3. In-Memory Incident Cache

- Successfully generated reports and their completion timestamps are stored in the in-memory `latest_incident_report` structure.
- Dashboard requests to `/api/dashboard-data` retrieve the cached report without initiating another LLM request.
- If the external LLM service is temporarily unavailable, telemetry ingestion and deterministic risk evaluation continue independently.
- Because the cache is process-local, its contents are cleared when the backend process restarts.

## Validation

### Telemetry Latency Validation

Endpoint response time should be measured both with and without an eligible background LLM dispatch.

The primary latency metric is:

$$
L_{\text{telemetry}} =
t_{\text{response sent}} -
t_{\text{request received}}
$$

The prototype design target is:

$$
L_{\text{telemetry}} < 10\text{ ms}
$$

under a defined local test environment and nominal system load, excluding client-to-server network latency.

This value is a performance objective rather than a verified guarantee. Validation should record:

- Python version;
- operating system;
- processor and available memory;
- dataset and serialized model versions;
- number of test requests;
- warm-up request count;
- median latency;
- 95th-percentile latency;
- maximum observed latency;
- whether an LLM task was dispatched.

The target should only be described as achieved after these measurements have been collected and reproduced.

### Cooldown Boundary Validation

A sequence of `CRITICAL` telemetry packets should be submitted at intervals shorter than 30 seconds. The test should confirm that:

- the first eligible critical packet dispatches an LLM task;
- subsequent critical packets inside the cooldown window do not dispatch additional tasks;
- a new task becomes eligible after the cooldown expires;
- non-critical telemetry does not trigger LLM generation.

For two request timestamps $t_i$ and $t_j$, where $t_j > t_i$, a second dispatch is valid only when:

$$
t_j - t_i
\ge
\texttt{LLM\_COOLDOWN\_SECONDS}
$$

### Cache Validation

The `/api/dashboard-data` endpoint should be queried before, during, and after background report generation to confirm that:

- telemetry remains available while report generation is pending;
- the previous report remains readable during the cooldown period;
- the cached report is updated after successful generation;
- dashboard reads do not initiate additional LLM requests.

### Failure-Isolation Validation

The external LLM client should be tested under simulated timeout, quota-limit, malformed-response, and network-failure conditions.

These failures must not:

- prevent `/api/telemetry` from returning its deterministic result;
- suppress the `action_required` signal;
- interrupt subsequent telemetry ingestion;
- replace a valid cached report with an incomplete result.

### Sustained-Critical-Event Validation

A continuous critical telemetry stream should be simulated for at least 60 seconds.

With a 30-second cooldown, the number of dispatched LLM tasks should remain bounded to approximately two requests per minute instead of one request per telemetry packet.

## Consequences

### Positive

- **Responsive telemetry ingestion:** The request path does not wait for external LLM inference.
- **Cost and quota protection:** Cooldown enforcement substantially reduces duplicate API consumption.
- **Immediate safety response:** The deterministic response and `action_required` value remain available independently of report generation.
- **Failure isolation:** External API failures do not interrupt deterministic risk evaluation.
- **Reduced report duplication:** Sustained critical conditions do not continuously generate nearly identical reports.

### Negative and Trade-offs

- **Initial report delay:** The first incident report becomes available only after background generation finishes.
- **Closely spaced incidents:** Two distinct incidents occurring inside the same cooldown window may not receive separate reports.
- **Process-local state:** Multiple application workers may maintain independent cooldown timers and caches.
- **Non-persistent cache:** Backend restarts clear the current report and cooldown state.
- **Task durability:** In-process background tasks may be lost if the application terminates before completion.
- **Fixed cooldown:** A static 30-second window may not be appropriate for every incident type.
- **Unverified latency target:** The telemetry latency objective requires benchmark evidence before being treated as an achieved performance result.

## Operational Constraints

The LLM-generated report is advisory and must not participate in the immediate safety-decision path.

The following outputs must remain independent of the external LLM:

- `final_risk`;
- `action_required`;
- local alarm triggers;
- telemetry acceptance;
- deterministic risk evaluation.

The deterministic risk engine, pessimistic safety gate, and edge-local actuation logic remain authoritative.

An LLM failure, timeout, quota error, or malformed response must not suppress or downgrade a critical alert.

## Future Considerations

For multi-worker or production deployments, the process-local cooldown and cache should be replaced with shared infrastructure such as:

- Redis-backed distributed locking;
- a persistent incident-report store;
- a durable task queue;
- incident identifiers for deduplication;
- event-aware cooldown invalidation;
- structured retry and exponential-backoff policies.

Any migration from process-local background tasks to distributed task execution should be documented in a new ADR that supersedes this decision.