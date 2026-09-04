# MineSentinel

MineSentinel is an edge-to-cloud monitoring and incident-management system for underground mining environments. It combines ESP32-based telemetry, deterministic safety rules, supervised and unsupervised machine-learning models, and asynchronous LLM-assisted incident reporting.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![ESP32](https://img.shields.io/badge/Hardware-ESP32%20%7C%20FreeRTOS-E7352C?logo=espressif&logoColor=white)](https://espressif.com/)
[![Scikit-learn](https://img.shields.io/badge/ML-Isolation%20Forest%20%7C%20Random%20Forest-F7931E?logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![Groq](https://img.shields.io/badge/LLM-Groq-F55036?logo=groq&logoColor=white)](https://groq.com/)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit%20Fragments-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Overview

Underground mining presents atmospheric and structural hazards that cannot be addressed reliably through a single detection method. Fixed thresholds provide predictable behavior but may be sensitive to sensor drift and changing operating conditions. Machine-learning models can identify multivariable patterns, but their probabilistic outputs should not override known physical safety limits.

MineSentinel combines four components:

1. **Deterministic risk engine:** Evaluates normalized sensor values against defined physical boundaries and includes a hard man-down or structural-collapse override.
2. **Isolation Forest:** Detects unmodeled hazards, sensor degradation, and unusual multivariable observations.
3. **Random Forest classifier:** Assigns telemetry to the operational classes `LOW`, `MEDIUM`, or `CRITICAL`.
4. **Groq incident reporting:** Generates incident summaries and evacuation recommendations asynchronously without blocking telemetry ingestion.

The system follows an edge-first design. Local alarms remain available on the ESP32 when backend connectivity is interrupted, while the backend performs risk arbitration, model inference, historical buffering, and dashboard delivery.

## System Architecture

```text
[Underground Edge Node]
  ESP32
  ├── MQ-2 gas sensor
  ├── MPU-6050 IMU
  ├── Warning LED
  └── Piezo siren
          |
          | HTTP POST /api/telemetry (~1.5 s)
          v
[FastAPI Telemetry Core]
  ├── Request validation
  ├── Deterministic risk engine
  ├── Isolation Forest
  ├── Random Forest classifier
  └── Pessimistic safety arbitration
          |
          ├── TelemetryResponse and local actuation command
          ├── CRITICAL + expired cooldown → background Groq report
          └── GET /api/dashboard-data
                    |
                    v
[Streamlit Operations Dashboard]
  ├── Fragment-based telemetry refresh
  ├── Plotly time-series charts
  ├── Risk indicators
  └── Incident reports
```

If Wi-Fi connectivity is lost, the ESP32 continues to evaluate local sensor thresholds and activates the warning outputs without waiting for a server response.

## Safety and Inference Design

### Pessimistic Safety Gating

The deterministic risk engine and Random Forest classifier are evaluated independently. The final operational class is selected using the more severe result:

$$
\text{final\_risk}
=
\max\left(
\text{severity}(R_{\text{level}}),
\text{severity}(\text{predicted\_risk})
\right)
$$

The risk engine produces a score $R \in [0,100]$, with scores greater than or equal to `70.0` classified as `CRITICAL`. A deterministic critical result cannot be downgraded by the machine-learning classifier.

This arbitration rule preserves known physical safety boundaries while retaining the classifier's ability to evaluate multivariable hazard patterns.

### Machine-Learning Pipeline

Inference operates on the feature vector:

$$
\mathbf{x} =
\begin{bmatrix}
\text{gas\_ppm} \\
\text{accel\_g} \\
\text{duration\_sec}
\end{bmatrix}
$$

| Model | Configuration | Responsibility |
|---|---|---|
| Isolation Forest | `contamination=0.20`, `n_estimators=100` | Detects sensor drift, unmodeled physical changes, and compound anomalies without labeled examples. |
| Random Forest | `class_weight="balanced"`, `n_estimators=100` | Classifies known hazard patterns as `LOW`, `MEDIUM`, or `CRITICAL` and returns class probabilities. |

Serialized models are stored in `models/` and loaded by the backend during application startup.

### Edge-Local Actuation

The ESP32 does not wait for a backend round trip before activating local safety outputs. Local alarm actuation triggers immediately under either of the following physical states:

1. **Instantaneous Environmental & Kinetic Thresholds:**
   $$
   \text{gas\_ppm} > 400.0
   \quad \lor \quad
   \text{accel\_g} > 2.0g
   \quad \lor \quad
   \text{accel\_g} < 0.4g
   $$

2. **Post-Impact Immobility (Man-Down State):**
   A sustained baseline reading ($\approx 1.0g$) evaluated across an elapsed dwell window ($T_{\text{dwell}} \ge 10\text{ s}$) following an acute kinetic impact event.

When either condition evaluates to true, the firmware asserts the warning LED and piezo siren directly via hardware GPIOs without waiting for a backend round-trip response.

### Asynchronous Incident Reporting

External LLM calls are not part of the immediate safety-decision path. When `final_risk == "CRITICAL"`, FastAPI dispatches incident-report generation through `BackgroundTasks` and returns the deterministic telemetry response without waiting for Groq.

A cooldown limits report generation during sustained incidents:

```text
LLM_COOLDOWN_SECONDS = 30.0
```

Critical packets received during the cooldown window reuse the most recently generated report. This limits duplicate reports, token consumption, and external API rate-limit exposure while telemetry ingestion continues at its normal frequency.

## Hardware

### Components and Pin Mapping

| Component | Interface | ESP32 GPIO | Operating Voltage | Function |
|---|---|---:|---:|---|
| MPU-6050 | I2C SDA | GPIO 21 | 3.3 V | Three-axis gyroscope and acceleration data |
| MPU-6050 | I2C SCL | GPIO 22 | 3.3 V | I2C clock at $100\text{ kHz}$ |
| MQ-2 | Analog ADC1 | GPIO 34 | 5.0 V VCC / 3.3 V ADC | Combustible-gas and smoke concentration |
| Warning LED | Digital output | GPIO 2 | 3.3 V, current-limited | Visual evacuation warning |
| Piezo siren | Digital output | GPIO 4 | 3.3 V / transistor gate | Acoustic warning |

> **Electrical note:** The MQ-2 module is powered at 5 V, but the ESP32 ADC input must not exceed 3.3 V. The analog signal path must remain within the ESP32's permitted input range.

## Repository Structure

```text
MineSentinel/
├── backend/
│   ├── ml/
│   │   ├── anomaly.py                          # Isolation Forest training and inference
│   │   └── classifier.py                       # Random Forest training and inference
│   ├── llm.py                                  # Groq generative crisis-reporting pipeline
│   ├── main.py                                 # FastAPI ingestion engine and safety arbitration
│   ├── risk_engine.py                          # Deterministic mathematical scoring engine
│   └── schemas.py                              # Pydantic V2 request and response contracts
├── dashboard/
│   └── dashboard.py                            # Streamlit operations SCADA dashboard
├── data/
│   ├── processed_sensor_data.csv               # Baseline calibration dataset
│   └── sample_sensor_data.csv                  # Raw/synthetic test telemetry
├── docs/
│   ├── decisions/                              # Architectural Decision Records (ADRs)
│   │   ├── 001_offline_first_and_connectivity.md
│   │   ├── 002_pessimistic_safety_gating.md
│   │   ├── 003_dual_model_ml_architecture.md
│   │   ├── 004_risk_score-design.md
│   │   ├── 005_isolation-forest_contamination.md
│   │   ├── 006_asynchronous_llm_reporting.md
│   │   └── 007_dashboard_fragment_rendering.md
│   ├── api_spec.md                             # HTTP and OpenAPI protocol specification
│   ├── demo_scenario.md                        # End-to-end evaluation and defense runbook
│   ├── hardware.md                             # Wiring schematics and sensor pinout specs
│   ├── ml_pipeline.md                          # Dual-model feature and training pipeline
│   └── risk_engine.md                          # Deterministic risk formulation specification
├── firmware/
│   └── mine_safety_esp32/
│       └── mine_safety_esp32.ino               # ESP32 telemetry and local-alarm firmware
├── models/
│   ├── anomaly_detector.joblib                 # Serialized Isolation Forest model
│   └── risk_classifier.joblib                  # Serialized Random Forest classifier
├── notebooks/
│   └── plot_data.py                            # Exploratory data analysis and visualization
├── scripts/
│   └── generate_sample_data.py                 # Synthetic sensor telemetry generator
├── .streamlit/
│   └── config.toml                             # Streamlit UI server and theme configuration
├── tests/
│   ├── test_api.py                             # Telemetry ingestion and endpoint tests
│   ├── test_models.py                          # ML model serialization and inference tests
│   └── test_risk_engine.py                     # Deterministic threshold validation suite
├── .env.example                                       # Environment variables (API keys, URLs)
├── .gitignore                                  # Git exclusion and tracking filters
├── CHANGELOG.md                                # Release notes and architectural evolution
├── ideas_for_v2.md                             # Roadmap and upcoming industrial features
├── LICENSE                                     # MIT License specification
├── README.md                                   # Primary system showcase and architecture vitrine
└── requirements.txt                            # Production runtime Python dependencies
```

## Getting Started

### Prerequisites

- Python 3
- `pip`
- A Groq API key for LLM-assisted incident reporting
- An ESP32 development environment when running the hardware firmware

### 1. Clone and Install

```bash
git clone https://github.com/beyzairemkaya/MineSentinel.git
cd MineSentinel
python -m venv venv
```

Activate the virtual environment:

```bash
# Linux or macOS
source venv/bin/activate

# Windows PowerShell
venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the repository root:

```env
GROQ_API_KEY="your-groq-api-key"
BACKEND_URL="http://localhost:8000"
```

Do not commit `.env` or API credentials to version control.

### 3. Start the Backend

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger UI is available at `http://localhost:8000/docs`.

### 4. Start the Dashboard

In a second terminal:

```bash
streamlit run dashboard/dashboard.py
```

The dashboard is available at `http://localhost:8501`.

### 5. Run the Test Suite

```bash
pytest tests/ -v
```

## API

### `POST /api/telemetry`

Evaluates an edge-sensor payload using the deterministic risk engine, anomaly detector, and supervised classifier.

#### Request

```json
{
  "gas_ppm": 650.0,
  "accel_g": 5.8,
  "duration_sec": 8.5,
  "miner_id": "MINER-EXP-04",
  "zone": "Shaft-7B"
}
```

#### Response

```json
{
  "miner_id": "MINER-EXP-04",
  "zone": "Shaft-7B",
  "risk_level": "CRITICAL",
  "confidence": 0.98,
  "class_probabilities": {
    "LOW": 0.01,
    "MEDIUM": 0.01,
    "CRITICAL": 0.98
  },
  "is_anomaly": true,
  "rule_risk_score": 88.5,
  "emergency_report": "CRITICAL HAZARD DETECTED: Simultaneous toxic gas surge (650 PPM) and acute structural kinetic shock (5.8g) detected at Shaft-7B. Evacuation protocol Alpha-1 initiated.",
  "action_required": true
}
```

The response operates as a low-latency design target because external LLM generation is handled asynchronously outside the immediate ingestion request path.

## Architecture Decision Records

Engineering decisions and trade-offs are documented in [`docs/decisions/`](docs/decisions/):

- [ADR 001: Offline-First and Edge-Autonomous Connectivity Strategy](docs/decisions/001_offline_first_and_connectivity.md)
- [ADR 002: Pessimistic Safety Gating and Arbitration Strategy](docs/decisions/002_pessimistic_safety_gating.md)
- [ADR 003: Dual-Model ML Architecture](docs/decisions/003_dual_model_ml_architecture.md)
- [ADR 004: Mathematical Risk Score Formulation and Threshold Calibration](docs/decisions/004_risk_score_design.md)
- [ADR 005: Isolation Forest Contamination Parameter Calibration](docs/decisions/005_isolation_forest_params.md)
- [ADR 006: Asynchronous LLM Incident Reporting and Rate-Limiting Cooldown](docs/decisions/006_asynchronous_llm_reporting.md)
- [ADR 007: Dashboard Fragment Rendering and Dynamic Configuration](docs/decisions/007_dashboard_fragment_rendering.md)

## Documentation

- [Hardware specification](docs/hardware.md)
- [API specification](docs/api_spec.md)
- [Machine-learning pipeline](docs/ml_pipeline.md)
- [Risk engine formulation](docs/risk_engine.md)
- [Demo scenario runbook](docs/demo_scenario.md)

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
