# ADR 003: Dual-Model Machine Learning Architecture (Unsupervised + Supervised)

## Status
Accepted

## Context
Underground mining operations present two fundamentally different classes of analytical challenges in real-time telemetry processing:
1. **Known, Quantifiable Hazard Classes:** Operational scenarios with well-defined physical patterns, such as sudden toxic gas surges, mechanical impact shocks, or post-collapse worker immobility. These states require deterministic classification into distinct tactical risk categories (`LOW`, `MEDIUM`, `CRITICAL`) with bounded confidence metrics so command personnel can execute predefined standard operating procedures (SOPs).
2. **Novelty & Zero-Day Anomalies:** Unforeseen environmental shifts, structural creep, sensor baseline drift, calibration degradation, or combined sub-threshold micro-disturbances. These anomalous states do not match known training distributions and cannot be reliably categorized into pre-labeled supervised classes without inducing false negatives.

Relying exclusively on a supervised classifier risks catastrophic misclassification on out-of-distribution physical telemetry. Conversely, relying exclusively on an unsupervised anomaly detector only flags binary deviance, failing to provide actionable classification or probabilistic confidence scores required for tiered rescue dispatch.

## Decision
We deploy a **Dual-Model Inference Architecture** that runs an unsupervised model alongside a supervised model in parallel within the FastAPI ingestion cycle:

1. **Unsupervised Layer (Isolation Forest):**
   * **Role:** Novelty detection, sensor fault detection, and zero-day hazard discovery.
   * **Algorithm:** `IsolationForest` (`n_estimators=100`, `contamination=0.20`, `random_state=42`).
   * **Execution:** Operates independently of labeled outcomes to isolate multi-dimensional outliers in the 3D feature space (`gas_ppm`, `accel_g`, `duration_sec`).
   * **Output:** A boolean outlier indicator (`is_anomaly: bool`).

2. **Supervised Layer (Random Forest Classifier):**
   * **Role:** Tactical risk classification and probabilistic hazard severity ranking.
   * **Algorithm:** `RandomForestClassifier` (`n_estimators=100`, `class_weight='balanced'`, `random_state=42`).
   * **Execution:** Maps normalized feature vectors into concrete tactical operational tiers (`LOW`, `MEDIUM`, `CRITICAL`).
   * **Output:** Discrete risk label (`predicted_risk`), confidence score ($[0.0, 1.0]$), and class posterior probabilities dictionary (`class_probabilities`).

3. **Inference Pipeline Integration:**
   * Both models consume the exact same sanitized 3-dimensional telemetry vector simultaneously without cross-dependency.
   * Ingestion responses synthesize outputs into a unified payload (`is_anomaly`, `predicted_risk`, `confidence`), enabling dashboard operators to identify cases where an event is categorized as `LOW` risk yet flagged as an anomalous outlier (`is_anomaly=True`), prompting immediate hardware diagnostic reviews.

## Consequences
### Positive
* **Defense-in-Depth:** Solves the blind spot of supervised-only systems by continuously screening for unmodeled mechanical or atmospheric anomalies.
* **Operational Actionability:** Operators receive clear operational categories for recognized hazards while retaining real-time flags for irregular sensor behavior.
* **Low Inference Overhead:** Both tree-based models run single-vector matrix inference in $< 2\text{ ms}$, preserving high-throughput requirements for real-time telemetry pipelines.

### Negative / Trade-offs
* **Dual Model Maintenance:** Serialization, lifecycle loading, version management, and retraining pipelines must maintain two distinct artifact files (`anomaly_detector.joblib` and `risk_classifier.joblib`).
* **Operator Ambiguity:** Edge cases where `is_anomaly=True` but `risk_level=LOW` require documented protocol guidelines so control room staff understand that sensor recalibration or environmental inspection is required rather than immediate tunnel evacuation.