# Machine Learning Pipeline & Hybrid Architecture

This document specifies the data pipeline, training protocols, feature representations, and dual-model inference architecture implemented in **MineSentinel**.

---

## 1. Architectural Strategy: Defense-in-Depth

Underground mining safety environments present two distinct analytical challenges:

1. **Known Hazard Signatures:** Gas concentration surges, structural impact g-forces, and worker immobility.
2. **Unmodeled Novel Anomalies:** Sensor calibration drift, progressive structural fractures, and atypical combined micro-disturbances.

To prevent single-point inference failures, MineSentinel pairs an **Unsupervised Anomaly Detector (Isolation Forest)** with a **Supervised Multi-Class Classifier (Random Forest)**, validated against a deterministic **Mathematical Risk Engine**.

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
  is_anomaly: bool                           risk_level: [LOW, MED, CRIT]
  (Novelty Detection)                        confidence: [0.0 - 1.0]
        |                                               |
        +-----------------------+-----------------------+
                                |
                                v
                   Unified Ingestion Response
```

## 2. Feature Representation Space

Inference operates over a 3-dimensional continuous feature vector:

$$
\mathbf{x} =
\begin{bmatrix}
\text{gas\_ppm} \\
\text{accel\_g} \\
\text{duration\_sec}
\end{bmatrix}
\in \mathbb{R}^3
$$

| **Feature**    | **Type** | **Physical Unit**       | **Operational Range** | **Baseline Value**    | **Description**                                       |
| -------------- | -------- | ----------------------- | --------------------- | --------------------- | ----------------------------------------------------- |
| `gas_ppm`      | Float    | Parts Per Million (PPM) | $150.0 - 1000.0$      | $\approx 150 - 220$   | Calibrated atmospheric gas reading from MQ-2.         |
| `accel_g`      | Float    | G-Force ($g$)           | $0.0 - 8.0$           | $\approx 0.98 - 1.02$ | Dynamic 3-axis magnitude vector from MPU-6050.        |
| `duration_sec` | Float    | Seconds ($s$)           | $0.0 - 30.0$          | $0.0$                 | Cumulative dwell timer for non-nominal hazard states. |

## 3. Unsupervised Outlier Detection: Isolation Forest

The **Isolation Forest** isolates observations by randomly selecting a feature and splitting the value. Because anomalies require fewer recursive splits to isolate than normal cluster points, their path lengths along isolation trees are noticeably shorter.

* **Model File:** `models/anomaly_detector.joblib`
* **Target:** Sensor malfunctions, zero-day hazards, structural instability outliers.

### Hyperparameter Configuration

* `n_estimators = 100`: Number of isolation trees in the ensemble.
* `contamination = 0.20`: Expected proportion of anomalous outliers in underground baseline calibration (refer to `docs/decisions/005_isolation_forest_params.md`).
* `random_state = 42`: Fixed seed for reproducible partition generation.

### Inference Mapping

$$
\text{Output} =
\begin{cases}
-1 \implies \text{is\_anomaly} = \text{True}
& (\text{Outlier / Hazard Anomaly}) \\
+1 \implies \text{is\_anomaly} = \text{False}
& (\text{Inlier / Nominal State})
\end{cases}
$$

## 4. Supervised Operational Classifier: Random Forest

The **Random Forest Classifier** maps the continuous telemetry vector into operational tactical classes used by evacuation systems and safety teams.

* **Model File:** `models/risk_classifier.joblib`
* **Target Classes:** `LOW`, `MEDIUM`, `CRITICAL`

### Hyperparameter Configuration

* `n_estimators = 100`: Number of decision trees.
* `criterion = 'gini'`: Impurity measurement metric.
* `class_weight = 'balanced'`: Adjusts weights inversely proportional to class frequencies to prevent bias towards nominal baseline states.
* `random_state = 42`: Deterministic split reproducibility.

### Training Protocol & Stratification

* **Dataset Partition:** 80% Train, 20% Holdout Test.
* **Stratification:** `stratify=y` enforced during split to ensure equal class proportions across partitions.
* **Outputs Generated per Request:**

  1. `risk_level`: Predicted label ($\arg\max P(Y = c \mid \mathbf{x})$).
  2. `confidence`: Peak class posterior probability ($\max P(Y = c \mid \mathbf{x})$).
  3. `class_probabilities`: Complete dictionary over all target labels:

     $$
     \left\{
     \text{"LOW"}: p_1,\;
     \text{"MEDIUM"}: p_2,\;
     \text{"CRITICAL"}: p_3
     \right\}
     $$

## 5. Model Serialization & Runtime Lifecycle

* Pre-trained models are persisted via `joblib` inside the `models/` directory.
* The FastAPI backend loads serialized models once into memory during application lifespan startup (`@asynccontextmanager`), ensuring zero disk I/O overhead during HTTP telemetry evaluation.
