# ADR 001: Offline-First & Edge-Autonomous Connectivity Strategy

## Status
Accepted

## Context
Underground mining environments present extreme wireless degradation challenges, including rock attenuation, multipath interference, gallery cave-ins, and communication trunk severance. If the life-safety warning mechanism relies entirely on an HTTP round-trip from a central cloud or local gateway server, any link outage directly causes unmitigated worker casualties.

## Decision
We enforce an **Edge-First / Offline-First Autonomous Protocol** directly within the ESP32 edge microcontroller firmware:
1. **Local Autonomous Hazard Actuation:** Sensor readings (MQ-2 gas concentration and MPU-6050 kinetic impact) are evaluated locally on each firmware cycle against fixed safety limits. If gas exceeds $400\text{ PPM}$ or acceleration deviates past impact/free-fall thresholds ($> 2.0g$ or $< 0.4g$), the ESP32 drives GPIO 2 (LED) and GPIO 4 (Buzzer) immediately, without awaiting server acknowledgment.
2. **Asynchronous Uplink:** HTTP POST transmission to `/api/telemetry` acts as an informational telemetry link for centralized SCADA monitoring, forensic logging, and tactical AI reporting—not as a blocking prerequisite for local life preservation.
3. **Non-Blocking Network Recovery:** When Wi-Fi connectivity drops, the firmware triggers background reconnection routines (`WiFi.reconnect()`) without halting local sensor sampling loops or muting active hardware sirens.

## Consequences
### Positive
* **Zero-Latency Life Safety:** Acoustic and visual evacuation warnings trigger at wire-speed ($< 5\text{ ms}$) on the helmet/wearable node.
* **Fault Tolerance:** Complete communication failure does not degrade local hazard detection or worker alerting.
* **Network Decoupling:** Transient packet losses or server latency spikes do not impact frontline physical protection.

### Negative / Trade-offs
* Complex multi-miner spatial coordination and evacuation routing (which rely on the central LLM/dashboard) require network connectivity.
* Historical telemetry logging at the central server experiences gaps during communication blackouts unless local non-volatile flash buffers (SPIFFS/EEPROM) are introduced.