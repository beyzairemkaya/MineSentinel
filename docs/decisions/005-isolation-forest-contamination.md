# Isolation Forest Contamination Parameter

## Context

Isolation Forest requires an estimate of the expected proportion
of anomalous observations in the dataset.

## EDA Findings

After processing the 1,000-row synthetic dataset with the
rule-based RiskEngine:

- LOW: 79.3%
- MEDIUM + CRITICAL: 20.7%

## Decision

The `contamination` parameter was initially set to `0.20`.

## Rationale

The value was selected based on the observed proportion of
higher-risk observations in the initial synthetic dataset.

This provides a data-driven starting point rather than selecting
the parameter arbitrarily.

## Validation

...

## Limitations

The dataset is synthetic, so the observed anomaly ratio does not
represent the actual anomaly rate in mining environments.

The parameter should be recalibrated using real-world sensor
data in a production deployment.