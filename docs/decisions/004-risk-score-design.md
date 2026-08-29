# Risk Score Design

## Objective

The Risk Engine converts sensor measurements into a single
risk score between 0 and 100.

The purpose of this score is to provide an interpretable
summary of the current safety condition.

## Formula

R_base = (w_gas × G_norm) +
         (w_accel × A_norm) +
         (w_duration × T_norm)

Risk Score = R_base × 100

## Feature Weights

| Feature | Weight | Reason |
|---|---:|---|
| Gas | 0.40 | Represents environmental hazard |
| Acceleration | 0.40 | Represents fall/impact risk |
| Duration | 0.20 | Represents persistence of the event |

## Normalization

### Gas

Raw gas measurements are normalized to [0, 1].

### Acceleration

Acceleration measurements are normalized to [0, 1].

### Duration

Event duration is normalized to [0, 1].

## Thresholds

| Score | Level |
|---:|---|
| 0–30 | LOW |
| 30–70 | MEDIUM |
| 70–100 | CRITICAL |

## Rationale

### Why these weights?

Gas and acceleration were assigned equal weights because both represent major safety risks in the initial prototype. Duration was given a lower weight because it is intended to modify the severity of an ongoing event rather than act as the primary hazard indicator.

### Why these thresholds?

Our weight distribution is defined as $w_{\text{gas}} = 0.40$, $w_{\text{acceleration}} = 0.40$, and $w_{\text{duration}} = 0.20$. Based on this mathematical model, the thresholds were selected according to the following rationale:

$0 - 30$ (LOW / Safe Zone): Sensor noise and normal operational movements can raise the overall score to approximately the $15%-25%$ range at most. Values below $30$ are therefore used to filter out false positives.
$30 - 70$ (MEDIUM / Isolated Hazard): If a single sensor reaches its maximum level, the maximum theoretical score it can contribute is approximately $40-60$ points (e.g., Gas at maximum $= 40$ points + Duration $= 10-20$ points $\rightarrow 50-60$ points). Therefore, the $30-70$ range represents an isolated hazard.
$70 - 100$ (CRITICAL / Combined Crisis): Mathematically, it is impossible for a single sensor to raise the score above $70$ on its own; at least two major risk sources (e.g., high gas levels + a severe fall/impact) must be triggered simultaneously. Therefore, $70+$ is defined as the emergency evacuation threshold.

## Design Considerations

The risk score is intentionally deterministic and
interpretable. The same sensor inputs should always
produce the same risk score.

## Limitations

These weights and thresholds are prototype-level design
choices.

They are not certified mine-safety thresholds and should
not be interpreted as such.

Real-world deployment would require calibration using
field data and relevant safety standards.