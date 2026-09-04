# ADR 005: Isolation Forest Contamination Parameter Calibration

## Status

Accepted

## Context

The unsupervised Isolation Forest algorithm isolates observations by randomly selecting a feature and splitting the resulting feature space. Anomalous observations generally require fewer recursive partitions to isolate than observations located within dense, nominal regions.

A critical hyperparameter of the Isolation Forest ensemble is `contamination`, which represents the expected proportion of anomalous observations in the training dataset. During model fitting, this value is used to derive the anomaly-score threshold $\tau$ that separates inliers from outliers:

$$
\hat{y}(\mathbf{x}) =
\begin{cases}
-1, & s(\mathbf{x}, n) \ge \tau \\
+1, & s(\mathbf{x}, n) < \tau
\end{cases}
$$

where:

* $s(\mathbf{x}, n)$ is the anomaly score assigned to observation $\mathbf{x}$;
* $\tau$ is the decision threshold determined during model fitting;
* $-1$ represents an outlier;
* $+1$ represents an inlier.

Setting `contamination` arbitrarily—or leaving the Scikit-learn configuration at its generic default of `'auto'`—risks producing an operationally uncalibrated decision boundary. Excessive sensitivity may flood underground safety operators with false anomaly alarms, while insufficient sensitivity may fail to identify meaningful physical or structural deviations.

## Exploratory Data Analysis Findings

Exploratory data analysis was performed over a baseline dataset containing 1,000 observations generated across the defined operational mining envelope. Each observation was independently evaluated by the deterministic `RiskEngine`.

The resulting operational distribution was:

* **Nominal Baseline (`LOW`):** 79.3% — 793 observations
* **Elevated Risk (`MEDIUM` + `CRITICAL`):** 20.7% — 207 observations

| Operational Category                           | Observation Count |      Share |
| ---------------------------------------------- | ----------------: | ---------: |
| Nominal Ambient Conditions (`LOW`)             |               793 |      79.3% |
| Elevated Risk Envelope (`MEDIUM` + `CRITICAL`) |               207 |      20.7% |
| **Total**                                      |         **1,000** | **100.0%** |

The empirically observed elevated-risk proportion is therefore:

$$
p_{\text{elevated}}
=
\frac{N_{\text{MEDIUM}} + N_{\text{CRITICAL}}}{N_{\text{total}}}
=
\frac{207}{1000}
=
0.207
$$

## Decision

The Isolation Forest `contamination` hyperparameter is fixed at `0.20` in `backend/ml/anomaly.py`:

```python
self.model = IsolationForest(
    n_estimators=100,
    contamination=0.20,
    random_state=42
)
```

This value must remain explicitly declared in the model configuration rather than relying on the library default.

## Rationale

The selection of `contamination = 0.20` is grounded in the elevated-risk proportion identified during exploratory analysis:

$$
0.207 \approx 0.20
$$

The absolute approximation error is:

$$
|0.207 - 0.20| = 0.007
$$

This corresponds to a difference of $0.7$ percentage points. For a dataset containing 1,000 observations, the configured contamination rate establishes an expected outlier count of approximately:

$$
N_{\text{outlier}}
=
N_{\text{total}} \times \text{contamination}
=
1000 \times 0.20
=
200
$$

The deterministic risk engine identified 207 elevated-risk observations. The difference between the two estimates is therefore:

$$
\Delta N = |207 - 200| = 7
$$

Because the Isolation Forest operates as an unsupervised anomaly detector rather than a tactical risk classifier, its predictions are not expected to reproduce deterministic risk labels exactly. The two components represent different analytical perspectives:

* The Isolation Forest detects statistically isolated feature combinations.
* The deterministic `RiskEngine` identifies observations that exceed predefined operational risk rules.
* The Random Forest predicts the most likely tactical risk class.

Calibrating the Isolation Forest to the approximate elevated-risk tail ensures that its anomaly boundary reflects the observed non-nominal proportion without treating deterministic risk labels as unsupervised training targets.

## Validation

### Outlier-Rate Validation

After fitting, the predicted anomaly rate must be calculated as:

$$
\hat{p}_{\text{anomaly}}
=
\frac{1}{N}
\sum_{i=1}^{N}
\mathbb{1}\left[\hat{y}_i = -1\right]
$$

For the 1,000-observation calibration dataset, the expected anomaly rate should remain approximately equal to the configured contamination value:

$$
\hat{p}_{\text{anomaly}} \approx 0.20
$$

Minor differences may occur because of tied anomaly scores at the learned decision boundary.

### Inlier/Outlier Alignment

The unsupervised anomaly mask (`is_anomaly`) must be compared with the deterministic risk labels to verify that anomaly flags concentrate primarily within the non-nominal operational envelope.

The following diagnostic table should be generated during validation:

|                                      | Predicted Inlier | Predicted Anomaly |
| ------------------------------------ | ---------------: | ----------------: |
| Deterministic `LOW`                  |    True Negative |    False Positive |
| Deterministic `MEDIUM` or `CRITICAL` |   False Negative |     True Positive |

The alignment metrics are defined as:

$$
\text{Precision}
=
\frac{TP}{TP + FP}
$$

$$
\text{Recall}
=
\frac{TP}{TP + FN}
$$

$$
F_1
=
2 \cdot
\frac{\text{Precision} \cdot \text{Recall}}
{\text{Precision} + \text{Recall}}
$$

These metrics are diagnostic rather than direct optimization objectives because the deterministic risk labels and unsupervised anomaly predictions represent different decision mechanisms.

### Feature-Pattern Inspection

Flagged anomalies must be manually or programmatically inspected to confirm that the detector is isolating meaningful multi-variable deviations, including combinations such as:

* elevated gas concentration with prolonged hazard duration;
* abnormal acceleration magnitude with extended immobility;
* simultaneous deviations across gas, acceleration, and duration;
* feature combinations located outside the nominal baseline cluster.

This inspection guards against a model that satisfies the expected anomaly proportion while isolating operationally irrelevant observations.

### Deterministic Reproducibility

The fixed pseudo-random state:

```python
random_state=42
```

ensures that repeated training runs using identical data and dependency versions produce consistent isolation-tree construction and prediction boundaries. This supports reproducible local testing and CI/CD validation.

Reproducibility must be verified by fitting the model multiple times on the same ordered dataset and confirming that the resulting anomaly masks are identical.

### Boundary Stability

The selected value should also be evaluated against nearby contamination settings, such as `0.15`, `0.20`, and `0.25`. The purpose of this sensitivity analysis is to verify that small parameter changes do not produce an operationally unstable anomaly boundary.

The `0.20` configuration remains acceptable when:

* the predicted outlier rate is consistent with the configured proportion;
* anomalies remain concentrated around non-nominal feature combinations;
* nominal sensor variation does not dominate the anomaly set;
* repeated fitting produces identical predictions under the fixed random seed.

## Consequences

### Positive

* **Empirical Grounding:** The hyperparameter is derived from the observed exploratory baseline rather than selected arbitrarily.
* **Controlled Sensitivity:** The expected anomaly rate is aligned with the approximate size of the non-nominal operational tail.
* **Reduced False-Alarm Pressure:** Nominal drilling and excavation micro-vibrations are less likely to dominate the anomaly set.
* **Reproducibility:** The explicit contamination value and fixed random seed support consistent model training and automated validation.
* **Architectural Independence:** The anomaly detector remains unsupervised and does not use deterministic risk labels as training targets.

### Negative / Trade-offs

* **Distribution Sensitivity:** If operational conditions shift significantly—for example, in deeper shafts with higher ambient gas concentrations—a static `0.20` threshold may incorrectly classify baseline observations as anomalies.
* **Synthetic-Baseline Dependence:** The selected value reflects the current 1,000-observation baseline and may not accurately represent anomaly prevalence in real-world telemetry.
* **Forced Outlier Proportion:** A fixed contamination value causes the model to reserve approximately 20% of the calibration distribution for outliers, even if the true operational anomaly rate differs.
* **Label–Anomaly Mismatch:** Elevated deterministic risk does not necessarily imply statistical isolation, and a statistically isolated observation does not necessarily represent an operational hazard.
* **Recalibration Requirement:** Production deployment requires recalibration against long-term telemetry collected from each operational shaft or environmental domain.

## Recalibration Triggers

The contamination parameter must be reviewed when any of the following conditions occurs:

* deployment to a new mine, shaft, or environmental domain;
* replacement or recalibration of the MQ-2 or MPU-6050 sensors;
* material drift in baseline gas or acceleration distributions;
* sustained changes in anomaly-alert frequency;
* unacceptable false-positive or false-negative behavior;
* significant modification of the synthetic data-generation process;
* accumulation of sufficient real-world telemetry to replace the synthetic baseline.

Any permanent change to the contamination value must be documented through a new ADR or a superseding revision of this decision record.
