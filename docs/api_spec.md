# REST API Specification & Data Contracts

This document defines the API interfaces, Pydantic schemas, validation rules, and data transfer contracts used in the **MineSentinel AIoT Safety Platform**.

---

## 1. Service Overview

- **Base URL:** `http://localhost:8000`
- **Protocol:** HTTP/1.1 – JSON
- **Framework:** FastAPI
- **Documentation:**
  - Swagger UI: `http://localhost:8000/docs`
  - ReDoc: `http://localhost:8000/redoc`

---

## 2. Health Check Endpoint

Used by monitoring systems and edge devices to verify backend availability.

### `GET /`

#### Response (`200 OK`)

```json
{
  "status": "online",
  "system": "MineSentinel Safety Core",
  "version": "1.0.0"
}
```

---

## 3. Telemetry Ingestion Endpoint

Receives real-time sensor packets from ESP32 devices or synthetic data generators.

### `POST /api/telemetry`

#### Request Headers

| Header | Value | Required |
|----------|---------|-----------|
| `Content-Type` | `application/json` | Yes |

---

### Request Body (`TelemetryInput`)

```json
{
  "miner_id": "MINER-01",
  "zone": "Sector-3",
  "gas_ppm": 210.5,
  "accel_g": 1.02,
  "duration_sec": 0.0
}
```

### Field Definitions

| Field | Type | Required | Constraints | Description |
|---------|--------|------------|----------------|----------------|
| `miner_id` | `string` | Yes | Min length: 1 | Unique worker or helmet identifier |
| `zone` | `string` | Yes | Min length: 1 | Mine sector or tunnel identifier |
| `gas_ppm` | `float` | Yes | `>= 0.0` | Estimated gas level derived from MQ-2 sensor readings |
| `accel_g` | `float` | Yes | `>= 0.0` | Acceleration magnitude from MPU6050 |
| `duration_sec` | `float` | Yes | `>= 0.0` | Duration of the current hazard condition |

---

### Processing Pipeline

Incoming telemetry is processed by:

1. **Risk Engine**
   - Rule-based risk score (`0–100`)

2. **Isolation Forest**
   - Unsupervised anomaly detection

3. **LLM Module**
   - Emergency report generation for critical events

---

### Response (`200 OK`)

```json
{
  "miner_id": "MINER-01",
  "zone": "Sector-3",
  "risk_level": "LOW",
  "rule_risk_score": 12.4,
  "is_anomaly": false,
  "emergency_report": null,
  "action_required": false
}
```

### Response Fields

| Field | Type | Description |
|---------|---------|----------------|
| `miner_id` | `string` | Worker identifier |
| `zone` | `string` | Mine zone |
| `risk_level` | `string` | `LOW`, `MEDIUM`, or `CRITICAL` |
| `rule_risk_score` | `float` | Risk score between `0-100` |
| `is_anomaly` | `boolean` | Isolation Forest anomaly flag |
| `emergency_report` | `string \| null` | LLM-generated emergency report |
| `action_required` | `boolean` | Indicates whether intervention is needed |

---

### Error Responses

#### `422 Unprocessable Entity`

Returned when:

- Required fields are missing
- Invalid data types are supplied
- Negative values are provided

Example:

```json
{
  "detail": "gas_ppm must be >= 0"
}
```

#### `500 Internal Server Error`

Unexpected backend or inference errors.

---

## 4. Dashboard Data Endpoint

Provides recent telemetry history and the latest incident report.

### `GET /api/dashboard-data`

#### Response (`200 OK`)

```json
{
  "telemetry_history": [
    {
      "timestamp": 1788442411.8,
      "gas_ppm": 210.5,
      "accel_g": 1.02,
      "duration_sec": 0.0,
      "risk_level": "LOW",
      "rule_risk_score": 12.4,
      "is_anomaly": false
    }
  ],
  "latest_incident": {
    "report": "Critical gas increase detected in Sector-3.",
    "timestamp": 1788442425.3
  }
}
```

### Field Definitions

| Field | Type | Description |
|---------|---------|----------------|
| `telemetry_history` | `array` | Rolling telemetry buffer |
| `latest_incident` | `object` | Most recent incident report |

---

## 5. Incident Generation Workflow

When:

```text
risk_level == "CRITICAL"
```

the backend performs:

### Background Processing

- Telemetry response returns immediately
- LLM runs asynchronously
- Dashboard remains responsive

### Cooldown Protection

```text
LLM_COOLDOWN_SECONDS = 30
```

Prevents:

- Excessive API calls
- Rate limit violations
- Repeated report generation

---

## 6. Validation Rules

### Sensor Constraints

```text
gas_ppm >= 0
accel_g >= 0
duration_sec >= 0
```

### Risk Thresholds

| Score | Level |
|---------|----------|
| 0 - 30 | LOW |
| 30 - 70 | MEDIUM |
| 70 - 100 | CRITICAL |

---

## 7. Limitations

- Sensor values are prototype-level measurements.
- MQ-2 gas estimates are not calibrated industrial PPM values.
- Thresholds are experimental and intended for demonstration purposes.
- Real deployment requires field calibration and safety certification.

---

## Version

MineSentinel API Specification v1.0