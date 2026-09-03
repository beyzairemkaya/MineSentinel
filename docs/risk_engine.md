# Risk Engine Mathematical Design & Specification

The **MineSentinel Risk Engine** is a hybrid deterministic rule engine that translates raw sensor telemetry into a bounded numerical risk index ($0.0 - 100.0$) and categorizes it into discrete operational alert levels. It acts as an explainable baseline layer alongside the machine learning classifiers.

---

## 1. Mathematical Formulation

The overall composite risk score ($R$) is calculated as a weighted linear combination of normalized physical parameters:

$$R = \left( w_{\text{gas}} \cdot G_{\text{norm}} + w_{\text{accel}} \cdot A_{\text{norm}} + w_{\text{duration}} \cdot D_{\text{norm}} \right) \times 100$$

### Weight Configuration
To maintain strict bounds ($0 \le R \le 100$), the sum of all scalar weights satisfies the unity constraint:

$$\sum w_i = w_{\text{gas}} + w_{\text{accel}} + w_{\text{duration}} = 1.0$$

* $w_{\text{gas}} = 0.40$ (Atmospheric toxic gas concentration)
* $w_{\text{accel}} = 0.35$ (Kinematic impact / fall dynamics)
* $w_{\text{duration}} = 0.25$ (Hazard exposure time)

---

## 2. Feature Normalization & Saturation Limits

All incoming telemetry attributes are transformed into unit scale $[0.0, 1.0]$ using localized bounds and saturation clipping (`np.clip`).

### A. Toxic Gas Normalization ($G_{\text{norm}}$)
* **Baseline Ambient:** $150.0\text{ PPM}$
* **Max Critical Ceiling:** $1000.0\text{ PPM}$
* **Equation:**
  $$G_{\text{norm}} = \text{clip}\left(\frac{\text{gas\_ppm} - 150.0}{850.0}, 0.0, 1.0\right)$$

### B. Dynamic Acceleration Normalization ($A_{\text{norm}}$)
Under nominal resting conditions, the accelerometer registers $1.0g$ (Earth gravity vector). Any deviation $|a - 1.0|$ indicates kinematic disturbance (free-fall or impact shock).

* **Baseline Gravity:** $1.0g$
* **Impact Saturation Span:** $4.0g$ ($5.0g$ absolute threshold)
* **Equation:**
  $$A_{\text{norm}} = \text{clip}\left(\frac{|a - 1.0|}{4.0}, 0.0, 1.0\right)$$

> **Design Rationale (Saturation / Clipping):**  
> In structural mine collapses or falls, kinetic impacts exceeding $5.0g$ represent severe physical trauma. Unbounded linear scaling would allow high acceleration spikes to overflow the risk index beyond $100.0$, overpowering atmospheric gas weighting. Capping the normalized output at $1.0$ guarantees that acceleration contributes proportionally without destabilizing the scoring index.

### C. Hazard Exposure Duration Normalization ($D_{\text{norm}}$)
Persistent danger is normalized linearly up to a 10-second ceiling:

$$D_{\text{norm}} = \text{clip}\left(\frac{\text{duration\_sec}}{10.0}, 0.0, 1.0\right)$$

---

## 3. Man-Down & Prolonged Immobility Rule

A critical failure mode in mining incidents is worker incapacitation following toxic gas inhalation or head trauma. To account for stationary victims who cannot generate acceleration spikes, an override rule is enforced:

$$\text{if } |a - 1.0| \le 0.08 \quad \text{and} \quad \text{duration\_sec} \ge 10.0 \implies R = \max(R, 75.0)$$

* **Mechanism:** If the miner remains motionless ($\approx 1.0g \pm 0.08g$) while an environmental hazard condition persists for $\ge 10$ seconds, the risk score is automatically clamped to a minimum floor of $75.0$, guaranteeing transition into the `CRITICAL` bracket.

---

## 4. Alert Level Boundaries

The continuous score $R \in [0.0, 100.0]$ maps into operational alert tiers based on static threshold brackets:

| Risk Score Range | Alert Level | Operational Protocol |
| :--- | :--- | :--- |
| $R < 30.0$ | **LOW** | Nominal monitoring; routine telemetry streaming. |
| $30.0 \le R \le 70.0$ | **MEDIUM** | Edge warning active (local buzzer/LED); supervisor alert. |
| $R > 70.0$ | **CRITICAL** | Automated evacuation alarm; triggers asynchronous LLM incident report. |