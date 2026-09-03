# Hardware Specification & Edge Architecture

This document specifies the hardware architecture, pinout configurations, sensor calibration procedures, and edge-level autonomous safety mechanisms of the **MineSentinel** IoT unit.

---

## 1. System Overview & Component Specifications

The edge device is designed around the **ESP32 NodeMCU-32S** development board (dual-core Xtensa 32-bit LX6, 240 MHz). It integrates atmospheric gas sensing, 6-DOF inertial measurement, and visual/auditory signaling hardware.

| Component | Part / Model | Operating Voltage | Interface | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Microcontroller** | ESP32-WROOM-32 | 3.3V (5V via Micro-USB) | Wi-Fi 802.11 b/g/n | Primary controller and edge processing unit |
| **Gas Sensor** | MQ-2 Semiconductor | 5V (VCC), 3.3V (Analog Out) | Analog (ADC1) | Flammable gases (LPG, Propane, Methane), Smoke |
| **IMU / Accelerometer** | MPU-6050 (GY-521) | 3.3V | I2C (`0x68`) | 3-axis accelerometer ($\pm 2g / \pm 8g$), 3-axis gyroscope |
| **Acoustic Alarm** | Active 5V Buzzer | 3.3V - 5V | Digital Output (GPIO) | High-decibel local emergency acoustic signaling |
| **Visual Alert** | High-Brightness Red LED| 3.3V (with 220Ω resistor) | Digital Output (GPIO) | Local emergency optical indicator |

---

## 2. Complete Pinout Matrix

To prevent ADC interference during Wi-Fi transmission, the analog sensor is routed exclusively to **ADC1**, avoiding ADC2 pins which are shared with the Wi-Fi radio subsystem.

| ESP32 Pin | Connected Peripheral | Peripheral Pin | Function | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **3V3** | MPU-6050 | VCC | 3.3V Power | Clean regulated 3.3V line |
| **VIN (5V)**| MQ-2 | VCC | 5V Power | Sensor heating coil requirement |
| **GND** | All Peripherals | GND | Common Ground | Common bus |
| **GPIO 21** | MPU-6050 | SDA | I2C Data | Internal pull-up enabled |
| **GPIO 22** | MPU-6050 | SCL | I2C Clock | Default 400 kHz Fast Mode |
| **GPIO 34** | MQ-2 | AOUT (Analog) | Analog Input | ADC1 Channel 6 (Input-only pin) |
| **GPIO 2**  | Active Buzzer | VCC / Signal | Digital Output | Active HIGH signaling |
| **GPIO 4**  | Red Warning LED | Anode (+) | Digital Output | In-line 220Ω current-limiting resistor |

---

## 3. Sensor Calibration & Signal Transformation

### A. MQ-2 Atmospheric Gas Mapping
The ESP32 12-bit ADC provides an integer resolution from `0` to `4095` ($0.0\text{V} - 3.3\text{V}$). The raw ADC output is mapped linearly into an atmospheric concentration representation ($150 - 1000\text{ PPM}$):

$$\text{gas\_ppm} = 150.0 + \left( \frac{\text{raw\_adc}}{4095.0} \times (1000.0 - 150.0) \right)$$

* **Ambient Baseline:** Under normal operating conditions, clean atmospheric air yields an ADC reading between $0$ and $400$ ($\approx 150 - 220\text{ PPM}$).
* **Hazard Threshold:** Readings above $400\text{ PPM}$ indicate elevated combustible gas concentration requiring edge alert actuation.

### B. MPU-6050 Inertial Vector Resolution
The MPU-6050 communicates via I2C at address `0x68`. The 3-axis accelerometer readings ($a_x, a_y, a_z$) are digitized in units of $g$ ($1g \approx 9.81\text{ m/s}^2$). The total composite kinematic acceleration ($a_{\text{mag}}$) is computed as the Euclidean norm:

$$a_{\text{mag}} = \sqrt{a_x^2 + a_y^2 + a_z^2}$$

* **Stationary Rest:** $a_{\text{mag}} \approx 1.0g \pm 0.05g$ (static Earth gravity).
* **Free-Fall / Instability:** $a_{\text{mag}} \to 0.0g$.
* **Impact / Structural Collapse:** $a_{\text{mag}} > 3.0g$.

---

## 4. Edge-First Autonomous Safety Logic

To ensure life safety under hazardous conditions, the edge device runs a deterministic local protection loop directly on the ESP32 firmware. **Auditory and visual alarms trigger concurrently without waiting for network or server acknowledgments.**

```text
                  +-----------------------+
                  |  Read MQ-2 & MPU-6050 |
                  +-----------+-----------+
                              |
              +---------------+---------------+
              |   Any Threshold Exceeded?     |
              |   - Gas > 400 PPM             |
              |   - Impact > 3.0g             |
              |   - Immobility >= 10s         |
              +---------------+---------------+
                     /                 \
                   YES                  NO
                   /                     \
      +------------------------+   +------------------------+
      |  TRIGGER COMBINED      |   |  STANDBY MODE          |
      |  EDGE ALARM:           |   |                        |
      |  - GPIO 2: Buzzer ON   |   |  - GPIO 2: Buzzer OFF  |
      |  - GPIO 4: LED ON/Blink|   |  - GPIO 4: LED OFF     |
      +-----------+------------+   +-----------+------------+
                  \                           /
                   +------------+------------+
                                |
                    +-----------v-----------+
                    | Serialize & Send HTTP |
                    | Payload to FastAPI    |
                    +-----------------------+