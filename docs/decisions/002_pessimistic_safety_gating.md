# ADR 002: Pessimistic Safety Gating & Arbitration Strategy

## Status
Accepted

## Context
Safety-critical industrial environments cannot rely exclusively on probabilistic machine learning models. Supervised classifiers (such as Random Forest) generalize patterns from training distributions, but they lack deterministic mathematical guarantees. When exposed to rare multi-sensor edge cases or sensor calibration drift, a probabilistic model can output an overly optimistic classification—such as predicting `MEDIUM` risk during an active `CRITICAL` hazardous event (e.g., severe worker incapacitation or prolonged toxic gas dwell time).

Conversely, a deterministic Risk Engine provides bounded, fully explainable mathematical scoring and hard threshold constraints (such as the Man-Down immobility override rule), but lacks non-linear pattern recognition across dynamic distributions. Running both subsystems concurrently without an explicit arbitration protocol creates ambiguity regarding which output governs life-safety actuation and emergency reporting.

## Decision
We implement a **Pessimistic Safety Gating (Worst-Case Arbitration)** pattern in the FastAPI ingestion pipeline (`backend/main.py`):

1. **Dual Independent Evaluation:**
   * Incoming telemetry is evaluated independently by the deterministic `RiskEngine` ($R \in [0.0, 100.0]$) and the trained `RiskClassifier`.
   * The numerical risk score is mapped into discrete operational tiers:
     $$R_{\text{level}} = \begin{cases} \text{CRITICAL}, & R \ge 70.0 \\ \text{MEDIUM}, & 30.0 \le R < 70.0 \\ \text{LOW}, & R < 30.0 \end{cases}$$

2. **Hierarchical Pessimistic Arbitration:**
   * A strict ordinal severity hierarchy is established:
     $$\text{CRITICAL} > \text{MEDIUM} > \text{LOW}$$
   * The final operational risk level is resolved as the maximum severity detected across either subsystem:
     $$\text{final\_risk} = \max\left(\text{severity}(R_{\text{level}}), \, \text{severity}(\text{predicted\_risk})\right)$$

3. **Deterministic Override:**
   * If the deterministic Risk Engine assesses an event as `CRITICAL` (e.g., via the Man-Down rule), it deterministically overrides any lower classification produced by the Random Forest model.
   * Downstream safety workflows—including `action_required` flags, rolling telemetry persistence, edge response payloads, and autonomous LLM emergency report generation—are strictly bound to `final_risk`.

## Consequences
### Positive
* **Zero Optimistic Failures:** A statistical blind spot or lower model confidence score can never suppress an active emergency alarm.
* **Formal Explainability:** Forensic post-incident investigations can trace whether an alert was triggered by statistical inference, deterministic boundary conditions, or both.
* **Compliance Alignment:** Complies with industrial functional safety principles (such as SIL guidelines), which require fail-safe deterministic overrides above black-box or statistical predictors.

### Negative / Trade-offs
* **Conservative Bias:** The false-positive rate will be slightly higher than that of an unconstrained statistical model, as edge anomalies triggering deterministic thresholds will always escalate to higher risk tiers.
* **Calibration Coupling:** Operational threshold updates in the Risk Engine must be tightly managed alongside model re-training cycles to prevent threshold divergence.