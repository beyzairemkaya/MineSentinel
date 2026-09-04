# Machine Learning Pipeline & Hybrid Architecture

This document specifies the data pipeline, training protocol, mathematical heuristics, and dual-model inference architecture implemented in **MineSentinel**.

---

## 1. Architectural Strategy: Defense-in-Depth

Underground mining safety systems face two distinct analytical challenges:
1. **Known Hazardous Patterns:** Toxic gas thresholds, structural impact shocks, and prolonged physical immobility.
2. **Unmodeled / Novel Anomalies:** Sensor drift, slow-developing structural fractures, and combined multi-vector micro-disturbances.

To handle both without single-point inference failures, MineSentinel pairs an **Unsupervised Anomaly Detector (Isolation Forest)** with a **Supervised Multi-Class Classifier (Random Forest)**, verified against a deterministic **Mathematical Rule Engine**.

```text
                        Telemetry Input
                 [gas_ppm, accel_g, duration_sec]
                                |
        +-----------------------+-----------------------+
        |                                               |
        v                                               v
+-----------------------+                       +-----------------------+
|   Isolation Forest    |                       |     Random Forest     |
| (Unsupervised Outlier)|                       | (Supervised Multi-Cls)|
+-----------+-----------+                       +-----------+-----------+
        |                                               |
        v                                               v
  is_anomaly: bool                                risk_level: [LOW, MED, CRIT]
  (Novelty Detection)                             confidence: [0.0 - 1.0]
        |                                               |
        +-----------------------+-----------------------+
                                |
                                v
                   Unified Ingestion Response