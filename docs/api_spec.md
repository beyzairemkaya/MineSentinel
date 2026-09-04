# REST API Specification and Data Contracts

This document defines the HTTP interfaces, Pydantic schemas, validation rules, and data contracts used by the **MineSentinel AIoT Safety Platform**.

---

## 1. Service Overview

- **Base URL:** `http://localhost:8000`
- **Protocol:** HTTP/1.1 with JSON
- **Framework:** FastAPI
- **API version:** `1.0.0`
- **Interactive documentation:**
  - Swagger UI: `http://localhost:8000/docs`
  - ReDoc: `http://localhost:8000/redoc`

---

## 2. Health Check Endpoint

### `GET /`

Returns the current API status and application version.

### Response — `200 OK`

```json
{
  "status": "online",
  "system": "MineSentinel Safety Core",
  "version": "1.0.0"
}
```

---

## 3. Telemetry Ingestion Endpoint

### `POST /api/telemetry`

Receives telemetry from an ESP32 edge device or a simulation client. Each request is evaluated by the deterministic risk engine, Isolation Forest anomaly detector, and Random Forest classifier.

### Request Headers

| Header | Value | Required |
|---|---|---|
| `Content-Type` | `application/json` | Yes |

### Request Body — `TelemetryInput`

```json
{
  "miner_id": "MINER-01",
  "zone": "Sector-3",
  "gas_ppm": 210.5,
  "accel_g": 1.02,
  "duration_sec": 0.0
}
```

### Request Fields

| Field | Type | Required | Default | Constraints | Description |
|---|---|---:|---|---|---|
| `gas_ppm` | `float` | Yes | — | `>= 0.0` | Estimated gas concentration derived from the MQ-2 reading |
| `accel_g` | `float` | Yes | — | `>= 0.0` | Total acceleration magnitude measured in gravitational units |
| `duration_sec` | `float` | Yes | — | `>= 0.0` | Duration of the detected event or post-impact immobility |
| `miner_id` | `string` | No | `UNKNOWN_DEVICE` | — | Edge device or miner identifier |
| `zone` | `string` | No | `UNKNOWN_ZONE` | — | Mine sector or monitored zone |

### Processing Pipeline

Incoming telemetry passes through the following stages:

1. **Request validation**
   - Pydantic validates required fields, data types, and numerical constraints.

2. **Deterministic risk engine**
   - Calculates an explainable risk score from `0.0` to `100.0`.
   - Applies the post-impact immobility override rule.

3. **Isolation Forest**
   - Determines whether the telemetry represents an anomaly.

4. **Random Forest classifier**
   - Predicts `LOW`, `MEDIUM`, or `CRITICAL`.
   - Returns prediction confidence and class probabilities.

5. **Pessimistic safety arbitration**
   - Compares the deterministic and classifier risk levels.
   - Selects the more severe result as `final_risk`.

6. **Incident reporting**
   - If `final_risk` is `CRITICAL` and the cooldown has expired, a Groq incident-report task is scheduled in the background.

### Safety Arbitration

The final operational risk level is calculated as:

```text
final_risk = max(rule_level, predicted_risk)
```

using the following severity order:

```text
LOW < MEDIUM < CRITICAL
```

A deterministic critical result therefore cannot be downgraded by the machine-learning classifier.

### Response — `200 OK`

```json
{
  "miner_id": "MINER-01",
  "zone": "Sector-3",
  "risk_level": "LOW",
  "confidence": 0.96,
  "class_probabilities": {
    "LOW": 0.96,
    "MEDIUM": 0.03,
    "CRITICAL": 0.01
  },
  "is_anomaly": false,
  "rule_risk_score": 1.0,
  "emergency_report": null,
  "timestamp": "2026-09-04T10:30:00.000000",
  "action_required": false
}
```

### Response Fields

| Field | Type | Description |
|---|---|---|
| `miner_id` | `string` | Device or miner identifier |
| `zone` | `string` | Mine sector or monitored zone |
| `risk_level` | `string` | Final risk level after pessimistic safety arbitration |
| `confidence` | `float` | Random Forest confidence value between `0.0` and `1.0` |
| `class_probabilities` | `object` | Probability distribution across `LOW`, `MEDIUM`, and `CRITICAL` |
| `is_anomaly` | `boolean` | Isolation Forest anomaly result |
| `rule_risk_score` | `float` | Deterministic risk score between `0.0` and `100.0` |
| `emergency_report` | `string \| null` | Latest available Groq-generated incident report |
| `timestamp` | `string` | UTC response-generation timestamp |
| `action_required` | `boolean` | `true` when the final risk level is not `LOW` |

> The `confidence` and `class_probabilities` fields describe the Random Forest output. The final `risk_level` may be higher than the classifier prediction when the deterministic risk engine activates the pessimistic safety gate.

> Incident reports are generated asynchronously. The response that triggers a new report may contain `null` or the previously cached report while generation is still in progress.

---

## 4. Error Responses

### `422 Unprocessable Entity`

Returned automatically by FastAPI when required telemetry fields are missing, numerical constraints are violated, or incompatible data types are supplied.

Example response:

```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": [
        "body",
        "gas_ppm"
      ],
      "msg": "Input should be greater than or equal to 0",
      "input": -10,
      "ctx": {
        "ge": 0.0
      }
    }
  ]
}
```

### `500 Internal Server Error`

Returned when model inference or another internal telemetry-processing operation fails.

Example response:

```json
{
  "detail": "Inference error: internal processing failure"
}
```

---

## 5. Dashboard Data Endpoint

### `GET /api/dashboard-data`

Returns the in-memory telemetry buffer and the latest generated incident report.

The telemetry buffer stores a maximum of 50 entries. Its contents are cleared when the backend process restarts.

### Response — `200 OK`

```json
{
  "telemetry_history": [
    {
      "timestamp": 1788442411.8,
      "gas_ppm": 210.5,
      "accel_g": 1.02,
      "duration_sec": 0.0,
      "risk_level": "LOW",
      "rule_risk_score": 1.0,
      "is_anomaly": false
    }
  ],
  "latest_incident": {
    "report": null,
    "timestamp": null
  }
}
```

### Response Fields

| Field | Type | Description |
|---|---|---|
| `telemetry_history` | `array` | Rolling in-memory buffer containing up to 50 telemetry results |
| `latest_incident` | `object` | Latest cached incident report and its generation timestamp |
| `latest_incident.report` | `string \| null` | Generated incident report, if available |
| `latest_incident.timestamp` | `float \| null` | Unix timestamp recorded after successful report generation |

---

## 6. Incident Generation Workflow

Incident-report generation is considered when:

```text
final_risk == "CRITICAL"
```

The backend then performs the following operations:

1. Checks the LLM cooldown.
2. Schedules `background_llm_task` when the cooldown has expired.
3. Returns the telemetry response without waiting for Groq.
4. Stores the generated report in the in-memory incident cache.
5. Exposes the report through `GET /api/dashboard-data`.

### Cooldown Protection

```text
LLM_COOLDOWN_SECONDS = 30.0
```

The cooldown reduces:

- duplicate incident reports;
- unnecessary API consumption;
- rate-limit exposure;
- repeated reports during sustained critical conditions.

The cooldown and incident cache are process-local and are reset when the backend restarts.

---

## 7. Validation and Risk Boundaries

### Sensor Constraints

```text
gas_ppm >= 0.0
accel_g >= 0.0
duration_sec >= 0.0
```

### Deterministic Risk Thresholds

| Score range | Risk level |
|---|---|
| `0.0 <= score < 30.0` | `LOW` |
| `30.0 <= score < 70.0` | `MEDIUM` |
| `70.0 <= score <= 100.0` | `CRITICAL` |

### Action Requirement

```text
action_required = final_risk != "LOW"
```

Therefore, both `MEDIUM` and `CRITICAL` responses request intervention.

---

## 8. Runtime Behavior

- Pre-trained models are loaded once during FastAPI application startup.
- Application startup fails if either serialized model cannot be loaded.
- Telemetry history is maintained in memory with a maximum length of 50.
- LLM generation runs outside the immediate risk-decision path.
- LLM failure does not suppress deterministic risk evaluation or `action_required`.
- Runtime state is not persisted across backend restarts.

---

## 9. Limitations

- Sensor values and thresholds are prototype-level.
- MQ-2 values are approximate mappings and are not calibrated industrial gas measurements.
- The machine-learning models are trained using synthetic prototype data.
- Risk thresholds are experimental and intended for demonstration.
- Telemetry history and incident reports are stored only in process memory.
- The system is not certified for production mine-safety deployment.
- Real deployment would require calibrated sensors, field validation, persistent storage, secure transport, authentication, redundancy, and applicable safety certification.

---

## Version

MineSentinel REST API Specification — Version 1.0