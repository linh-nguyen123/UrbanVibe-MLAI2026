# UrbanVibe: SafeRoute
## 5-Minute Live Demonstration Script & Jury Q&A Playbook
### MLAI Hackathon 2026 - Decision Intelligence Challenge (TMA Solutions)

---

### Timing Breakdown & Speaker Roles

* **Role 1 (Thien - Decision Intelligence & MCDA):** Minutes 00:00 – 02:00
* **Role 2 (Tam / Thinh - Edge AI, Audio Stream & Haptics):** Minutes 02:00 – 04:00
* **Role 3 (Linh - Product Lead & Governance):** Minutes 04:00 – 05:00

---

### Detailed Stage Timeline

#### Minutes 00:00 – 02:00 | Pre-Trip Decision Intelligence (Thien)
* **Goal:** Demonstrate transparent route optimization and Explainable AI.
* **Actions:**
  1. Open Streamlit Dashboard on Tab 1: Pre-Trip Decision Intelligence.
  2. Select Origin and Destination (e.g., District 1 to Thu Duc City).
  3. Switch between user preference presets: Safe-First vs Balanced vs Fast-First.
  4. Show how the Pareto Frontier Filter automatically eliminates dominated routes.
  5. Point out the Trade-Off Matrix:
     - Compare Route A (Fastest: 20 min, high acoustic risk ARI 8.2) vs Route B (SafeRoute: 27 min, ARI 1.8).
  6. Highlight the XAI Card narrative:
     - *"Route B is recommended: Takes 7.0 min longer (+30.4%) to reduce acoustic risk by 76.2% and avoids heavy truck corridors."*
  7. Click "Confirm & Start Route" to transition to Tab 2.

#### Minutes 02:00 – 04:00 | On-Trip Safeguard & Haptic Warnings (Tam & Thinh)
* **Goal:** Demonstrate real-time on-device audio classification and multimodal alerting.
* **Actions:**
  1. Show Tab 2 in Rider Mode (minimalist, high-contrast HUD for motorbike handlebar mount).
  2. Baseline state: Green HUD indicator (Safe Environment, ~50 dB ambient, zero haptics).
  3. Event 1 (Vehicle Horn): Trigger motorbike horn audio sample -> Visual HUD flashes warning border, Web Vibration API fires 2 sharp haptic pulses [150ms, 100ms, 150ms].
  4. Event 2 (Emergency Siren / Approaching Truck): Trigger siren audio -> Visual HUD turns flashing red with emergency directive ("PULL OVER RIGHT"), continuous rapid pulses [300ms, 100ms, 300ms].
  5. Emphasize low latency benchmark metrics on display: Inference Latency 14-18 ms, reaction time < 80 ms.

#### Minutes 04:00 – 05:00 | Fail-Safe Reliability, Privacy & Impact (Linh)
* **Goal:** Address reliability, privacy compliance, and commercial scalability.
* **Actions:**
  1. Demonstrate the three system health states: HEALTHY, DEGRADED, UNAVAILABLE (prevents silent failures if microphone or sensor is occluded).
  2. Privacy by Design: Emphasize 100% On-Device execution with Zero Raw Audio Storage (no audio files saved, compliant with Decree 13/2023/ND-CP).
  3. Commercial summary: 0 VND barrier for 2.5 million users today; modular hardware roadmap for fleet OEMs tomorrow.

---

### TMA Solutions Jury Q&A Playbook

1. **Q: How does the system handle high urban ambient noise (false alarms)?**
   - **Answer:** We employ a Dual-Threshold Gate. The system requires both semantic classification (YAMNet label confidence >= 0.60) AND physical acoustic intensity (dB SPL >= 75 dBA or dynamic jump >= +12 dBA). This filters out >98% of background urban chatter and distant sounds.

2. **Q: How is the Bayesian uncertainty parameter calculated?**
   - **Answer:** It follows $U(s) = \sigma_0^2 / \sqrt{N_{trips} + 1}$. Unexplored or sparse segments have high uncertainty penalty, ensuring the engine never erroneously labels an unobserved route as safe.

3. **Q: Does this replace the rider's visual awareness?**
   - **Answer:** No. UrbanVibe is explicitly designed as a Decision Support and Edge Safeguard tool. It assists with blind-spot acoustic awareness from behind without requiring screen interaction while driving.
