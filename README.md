# Cooperative Traffic Management in Construction Zones with V2X

This project proposes a cooperative control architecture based on V2X communications to mitigate the negative impacts of road construction zones. The system implements an intelligent infrastructure (RSU) that acts as a traffic mediator, broadcasting dynamic speed recommendations to vehicles in the vicinity.

The solution was developed and validated in the Eclipse MOSAIC co-simulation environment, directly coupled with the SUMO traffic simulator.

## 🛠️ Technologies and Tools
* **Traffic Simulator:** SUMO (Simulation of Urban MObility)
* **Co-simulation Environment:** Eclipse MOSAIC
* **Communication Protocol Stack:** ETSI ITS-G5

## ⚙️ System Architecture and Communications

The network infrastructure was designed to operate in high-density vehicular scenarios, rejecting blind flooding approaches.

* **Distance-Based Contention Forwarding (DBCF):** A channel congestion mitigation mechanism that prioritizes retransmission for receivers furthest from the message source.
* **Directional Geocasting:** A technique implemented to optimize radio channel usage, ensuring that vehicles outside the critical zone immediately silence the propagation chain.
* **Hysteresis Logic:** The RSU incorporates a conditional dual-threshold system to mitigate the constant oscillation of speed guidelines (ping-pong effect).
* **Kinetic Funneling:** The recommended speed is determined adaptively by the RSU based on traffic state and modulated by the receiver's distance to the construction zone.

## 🗺️ Simulation Scenario

* The main validation scenario consists of a 4x4 Manhattan grid network.
* The topology comprises 3 RSUs, 4 traffic light zones, and 4 roundabout zones.
* Stochastic traffic injection was generated via a Python script (randomTrips.py).
* Tests included driving profiles with different cooperative penetration rates (0%, 25%, 50%, and 100%).

## 📊 Main Results

Quantitative evaluation demonstrated that Edge coordination in adverse ITS environments requires a trade-off between maximum throughput and safety.

* **Shockwave Absorption:** The system significantly reduces extreme travel times (95th percentile), proving the absorption of shockwaves.
* **Predictability:** The architecture sacrifices raw throughput capacity in favor of flow safety and stability.
* **Network Resilience:** The DBCF algorithm allowed for the suppression of approximately 70% of redundant traffic on the ITS-G5 channel, eliminating the risk of broadcast storms.
* **Physical Stabilization:** The maximum queue length (spillback) shows clear stabilization at peak vehicular cooperation levels.
