# Changelog

All notable changes to the **MineSentinel** platform are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-09-04

### Added
- **Pessimistic Safety Gating Protocol:** Enforced deterministic mathematical safety arbitration where physical rule-based critical alerts strictly override statistical ML predictions.
- **Dual-Model ML Pipeline:** Integrated unsupervised zero-day anomaly screening (Isolation Forest) with supervised multi-class hazard triage (Random Forest).
- **Asynchronous LLM Triage:** Decoupled Groq generative crisis reporting from high-frequency telemetry loops using FastAPI `BackgroundTasks` with a 30-second rate-limiting cooldown.
- **Fragment-Based SCADA UI:** Implemented selective real-time DOM updates in Streamlit via `@st.fragment(run_every=2)` to eliminate interface flickering.
- **Edge-Autonomous Fail-Safe:** Configured ESP32 firmware with local GPIO hardware interrupts (piezo siren/strobe LED) ensuring uninterrupted life safety during Wi-Fi link dropouts.
- **Post-Impact Immobility Tracking:** Added Man-Down detection logic tracking gravitational rest state ($1.0g \pm 0.08g$) across a persistent 10-second dwell window.
- **Architectural Decision Records (ADRs):** Comprehensive technical rationales documented for design decisions (ADR 001 through ADR 007).
- **Automated Verification Suite:** Pytest suites covering deterministic risk thresholds, model inference pipelines, and API contract invariants.

### Changed
- Re-aligned deterministic risk scoring boundaries in `risk_engine.py` to ensure $R \ge 70.0$ strictly evaluates to `CRITICAL`.
- Standardized API contracts in `docs/api_spec.md` with explicit non-overlapping score intervals ($[0, 30)$, $[30, 70)$, $[70, 100]$) and default worker parameters.
- Reorganized firmware directories to comply with native Arduino IDE path conventions (`firmware/mine_safety_esp32/mine_safety_esp32.ino`).

### Fixed
- Fixed critical state-machine bug in firmware where post-impact immobility counter (`durationSec`) reset prematurely upon returning to $1.0g$.
- Resolved redundant dependency definitions in `requirements.txt` and pinned Streamlit minimum version to `1.33.0` for native fragment support.
- Corrected hyphenation and relative link targets across all Architectural Decision Records.

### Security
- Excluded dynamic runtime configuration and credentials (`.env`) from version control; established `.env.example` deployment template.
- Enforced input bounds validation on incoming sensor telemetry via Pydantic V2 schemas.