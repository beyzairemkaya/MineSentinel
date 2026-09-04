# MineSentinel v2.0 - Engineering Roadmap & Future Capabilities

This document outlines the architectural enhancements, hardware upgrades, and enterprise-scale features planned for the **MineSentinel v2.0** milestone.

---

## 1. Multi-Miner Fleet Coordination & Swarm Telemetry

The current v1 architecture arbitrates risks on discrete telemetry streams. Version 2.0 will transition from single-node monitoring to coordinated underground workforce management:

* **Correlated Sector Evacuations:** If a single miner experiences a `CRITICAL` atmospheric or shock event, the backend automatically calculates blast/hazard propagation vectors and raises cautionary alerts for all active units in the same tunnel sector.
* **Underground Personnel Density Mapping:** Live tracking of workforce distribution across sub-levels to prevent crowding in poorly ventilated dead-ends and optimize evacuation bottleneck routing.
* **Collective Man-Down Triage:** Automated clustering algorithm to distinguish between an isolated worker incident versus a localized tunnel collapse affecting multiple workers simultaneously.

---

## 2. Subterranean Mesh Networking (BLE / ESP-NOW / LoRa)

Underground RF environments suffer from severe multipath fading and rock absorption, making continuous Wi-Fi impractical across deep galleries:

* **ESP-NOW / LoRa Peer-to-Peer Mesh:** Edge nodes forward telemetry packets peer-to-peer across adjacent helmets/vests until reaching a wired gateway or leaky feeder antenna.
* **Store-and-Forward Black Box Buffering:** Nodes retain up to 30 minutes of high-resolution sensor telemetry locally in SPI flash memory during link blackouts, automatically syncing historical batches upon gateway reconnection.

---

## 3. Spatial Localization & Dead Reckoning (PDR)

GPS is fundamentally inoperable underground. Version 2.0 introduces infrastructure-free tracking:

* **Pedestrian Dead Reckoning (PDR):** Integrating step-counting, stride estimation, and heading direction via MPU-6050 accelerometer and gyroscope data.
* **Fixed BLE Beacons / UWB Nodes:** Anchor nodes placed along mine cross-cuts for sub-meter drift correction and absolute 3D coordinate mapping.

---

## 4. Hardware Hardening & Intrinsic Safety (ATEX)

* **Intrinsic Safety Compliance (ATEX / IECEx Zone 0):** Redesigning PCB traces, encasing components in potted flameproof enclosures, and limiting capacitive energy storage to prevent sparking in flammable methane environments.
* **Multi-Gas Optical Sensing:** Replacing the power-hungry MQ-2 with low-power Non-Dispersive Infrared (NDIR) sensors for selective carbon monoxide ($CO$), methane ($CH_4$), and oxygen depletion ($O_2$) monitoring.

---

## 5. Streaming Architecture & Distributed Backend

* **WebSocket / gRPC Duplex Streaming:** Migrating from HTTP polling ($0.5\text{ Hz}$) to bidirectional WebSocket / gRPC streams, enabling instantaneous server-push commands down to edge nodes.
* **Time-Series Engine Integration:** Incorporating InfluxDB or TimescaleDB for multi-year telemetry archiving, automated baseline retraining, and continuous sensor calibration drift tracking.