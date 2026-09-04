# ADR 007: Dashboard Fragment Rendering and Dynamic Configuration

## Status

Accepted

## Context

Underground mining command-and-control operations require a real-time Supervisory Control and Data Acquisition (SCADA) monitoring interface. The MineSentinel operations dashboard (`dashboard/dashboard.py`) is implemented using Streamlit to visualize continuous telemetry streams, sensor risk gauges, anomaly alerts, and automated LLM crisis reports.

However, standard real-time Streamlit architectures present two core engineering limitations:

1. **Full-Page Rerun Flickering:** Traditional real-time polling loops rely on `st.rerun()` or global `while True: time.sleep()` cycles. These primitives trigger a complete re-execution of the script from top to bottom. In an industrial dashboard, this causes the navigation sidebar, configuration controls, and report text boxes to redraw continuously. The resulting behavior creates severe visual flickering, may reset user-interface state, and degrades control-room usability.

2. **Hardcoded Networking Constraints:** Hardcoding local IP addresses or static ports directly in the frontend script prevents seamless transitions between local development environments, on-premises mine servers, and containerized Docker or Kubernetes deployments. This approach also violates the configuration principles of the Twelve-Factor App methodology.

## Decision

We enforce **isolated fragment rendering** and **environment-driven configuration** in `dashboard/dashboard.py`.

```text
+-------------------------------------------------------------------+
| MineSentinel SCADA Dashboard (Static Host Page)                   |
| - Sidebar Navigation and Manual Controls                          |
| - Incident Summary and Model Metrics                              |
| - Preserved Interface State                                       |
|                                                                   |
|   +-------------------------------------------------------------+ |
|   | @st.fragment(run_every=2)                                   | |
|   | Independent Real-Time Telemetry Fragment                    | |
|   |                                                             | |
|   | - Pulls GET /api/dashboard-data via dynamic BACKEND_URL     | |
|   | - Redraws Plotly time-series charts and risk gauges only    | |
|   | - Refreshes every 2 seconds without rerunning parent page   | |
|   +-------------------------------------------------------------+ |
+-------------------------------------------------------------------+
```

### 1. Selective Rendering via `@st.fragment`

High-frequency telemetry charts and risk-indicator cards are encapsulated within a dedicated function decorated with:

```python
@st.fragment(run_every=2)
def render_realtime_telemetry():
    ...
```

This architectural boundary provides the following behavior:

* Only isolated telemetry charts and real-time status indicators are rerun every two seconds.
* The static dashboard frame, incident-report sections, and control widgets remain outside the high-frequency refresh cycle.
* User interactions and interface state are preserved without requiring a complete application rerun.
* Real-time rendering logic remains separated from static dashboard composition.

The refresh interval is represented as:

$$
T_{\text{refresh}} = 2\text{ s}
$$

Therefore, the expected fragment refresh frequency is:

$$
f_{\text{refresh}}
=
\frac{1}{T_{\text{refresh}}}
=
\frac{1}{2}
=
0.5\text{ Hz}
$$

This results in approximately 30 telemetry refresh operations per minute:

$$
N_{\text{refresh per minute}}
=
\frac{60}{2}
=
30
$$

### 2. Twelve-Factor Dynamic Configuration with `BACKEND_URL`

The dashboard is decoupled from hardcoded backend addresses by reading the service URL from an environment variable with a safe local-development fallback:

```python
BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://localhost:8000",
)
```

The dashboard-data endpoint can then be constructed dynamically:

```python
dashboard_endpoint = f"{BACKEND_URL}/api/dashboard-data"
```

This configuration supports deployment across:

* local development environments;
* Docker Compose service networks;
* on-premises edge gateways;
* remote backend hosts;
* Kubernetes services and ingress endpoints;
* automated test harnesses.

The backend location can therefore be changed at runtime without editing or recompiling the dashboard source code.

### 3. Graceful Degradation During Network Partitions

Telemetry-fetch requests are wrapped in explicit HTTP error-handling logic. If the backend becomes temporarily unreachable, the dashboard must:

* avoid terminating the Streamlit application;
* preserve the last valid telemetry state when available;
* display a clear `Awaiting Telemetry Stream` indicator;
* distinguish temporary connection loss from a valid empty telemetry response;
* retry during the next scheduled fragment refresh.

The isolated fragment acts as a bounded failure domain. A failed telemetry request affects the real-time monitoring region without invalidating the static dashboard shell or unrelated operator controls.

## Validation

### Fragment-Isolation Validation

The dashboard must be observed during multiple telemetry-refresh cycles to confirm that:

* real-time charts update every two seconds;
* the sidebar does not visibly redraw;
* manually selected controls retain their values;
* static incident-report content remains stable;
* the complete application script is not explicitly rerun through `st.rerun()`.

### Configuration Validation

The dashboard must be launched under at least two configurations:

```bash
BACKEND_URL=http://localhost:8000
```

```bash
BACKEND_URL=http://backend:8000
```

The test should confirm that the same dashboard build connects to the selected backend without source-code modification.

If `BACKEND_URL` is not defined, the resolved configuration must be:

```text
http://localhost:8000
```

### Network-Failure Validation

The backend service must be temporarily stopped or made unreachable while the dashboard remains active. The dashboard should:

* continue rendering the static interface;
* display the connection-state indicator;
* avoid exposing an unhandled exception to the operator;
* recover automatically after backend connectivity is restored.

### State-Preservation Validation

Operator-controlled widget values must be recorded before several fragment refreshes and compared afterward. A successful validation requires the relevant session-state values to remain unchanged unless the operator explicitly modifies them.

Conceptually, for an operator-controlled state value $S$:

$$
S_{t+1} = S_t
$$

during fragment refreshes that do not contain an explicit user-state transition.

### Dependency Validation

The installed Streamlit version must satisfy:

$$
\text{Streamlit version} \ge 1.33.0
$$

This constraint must be represented explicitly in `requirements.txt` to ensure that `@st.fragment` is available in development, CI/CD, and deployment environments.

## Consequences

### Positive

* **Flicker-Free Monitoring:** Control-room operators observe continuous real-time data updates without repeated full-page redraws or unnecessary interface jitter.
* **State Preservation:** Navigation selections, configuration controls, and static report content remain stable during telemetry refreshes.
* **Portable Deployment:** The dashboard can connect to different edge or cloud backends by setting `BACKEND_URL` at runtime.
* **Reduced Client Resource Usage:** Rendering only the changing visual components reduces unnecessary browser and server-side processing during continuous operation.
* **Failure Isolation:** Temporary telemetry-fetch failures remain contained within the real-time fragment instead of terminating the complete dashboard.
* **Configuration Separation:** Environment-specific network addresses remain outside the application source code.

### Negative / Trade-offs

* **Streamlit Version Pinning:** The `@st.fragment` feature requires Streamlit version $\ge 1.33.0$, necessitating explicit dependency constraints in `requirements.txt`.
* **State Encapsulation Discipline:** Developers must avoid unsafe cross-mutation of shared session-state variables inside fragment scopes.
* **Fragment Complexity:** Data dependencies shared between the static page and the real-time fragment require carefully defined ownership.
* **Polling Overhead:** The dashboard continues to issue backend requests every two seconds even when telemetry has not changed.
* **Process Dependency:** Dashboard availability remains dependent on the Streamlit server and its active user session.
* **Configuration Validation:** Incorrectly formatted or unreachable `BACKEND_URL` values must be handled explicitly at runtime.

## Operational Constraints

The real-time fragment must not contain:

* unbounded `while True` polling loops;
* global `time.sleep()` calls used for page refresh;
* unconditional `st.rerun()` calls;
* direct mutation of unrelated operator-control state;
* hardcoded deployment-specific backend addresses.

The static dashboard layer remains responsible for:

* page configuration;
* navigation;
* manual controls;
* stable incident-report presentation;
* static model and system information.

The fragment layer remains responsible for:

* periodic telemetry retrieval;
* live sensor charts;
* risk gauges;
* connection-status indicators;
* bounded network-error handling.

## Future Considerations

If polling overhead or dashboard concurrency becomes a limiting factor, future revisions may evaluate:

* WebSocket-based telemetry streaming;
* Server-Sent Events;
* adaptive refresh intervals based on active risk level;
* HTTP caching and conditional requests;
* shared telemetry buffers across dashboard sessions;
* explicit connection-health metrics;
* distributed dashboard deployment.

Any migration from scheduled fragment polling to push-based streaming should be documented in a new ADR that supersedes this decision.
