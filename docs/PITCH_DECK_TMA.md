# UrbanVibe: SafeRoute
## Pitch Deck: TMA Solutions Decision Intelligence Challenge | MLAI Hackathon 2026

---

### Slide 1: Problem & Social Impact (Context & Motivation)
* **Title:** Empowering 2.5 Million Hearing-Impaired Vietnamese Riders
* **The Silent Hazard:**
  - Vietnam has over 2.5 million deaf and hard-of-hearing individuals navigating mixed traffic environments.
  - Vehicle horns (motorbikes, cars, emergency sirens) serve as vital collision warnings that hearing-impaired riders cannot detect from behind.
* **Core Mission:**
  - "We do not promise to replace visual observation; we turn acoustic risk, spatial uncertainty, and user preferences into transparent, explainable, and verifiable routing decisions."
* **Strategy:** Software-First MVP with 0 VND additional hardware cost, running entirely on standard smartphones.

---

### Slide 2: Pre-Trip Decision Intelligence (MCDA Core)
* **Title:** Transparent Multi-Criteria Route Optimization
* **Mathematical Foundation:**
  - **Pareto Frontier Filter:** Automatically eliminates dominated routes that are simultaneously slower, riskier, and more uncertain.
  - **Hard Safety Constraint:** Rejects any candidate route exceeding the peak acoustic threshold ($ARI_{max} > \tau_{cutoff}$).
  - **Weighted-Sum MCDA:**
    $$C(P) = w_{time} \cdot \left(\frac{T}{T_{max}}\right) + w_{ari} \cdot \left(\frac{ARI_{eval}}{10}\right) + w_{uncert} \cdot U(P)$$
    where $ARI_{eval} = 0.6 \cdot \overline{ARI} + 0.4 \cdot ARI_{P90}$.
  - **Bayesian Uncertainty Penalty:**
    $$U(s) = \frac{\sigma_0^2}{\sqrt{N_{trips} + 1}} \in [0, 1]$$
* **User-Driven Preferences:** Three standard presets (Safe-First, Balanced, Fast-First) with normalized weight vectors $\sum w_i = 1.0$.

---

### Slide 3: Two-Phase Architecture & Dual-Threshold Edge Gate
* **Title:** Edge-AI Acoustic Inference & Multimodal Feedback
* **Phase 1: Pre-Trip Route Selection:**
  - Interactive Trade-Off Matrix with quantitative risk reduction metrics.
  - Explainable AI (XAI) transparent narrative (e.g., "Takes 7.0 min longer to reduce acoustic risk by 78.8%").
* **Phase 2: On-Trip Real-Time HUD:**
  - On-device Google YAMNet TFLite INT8 (3.7 MB footprint, 14-18 ms inference latency).
  - Dual-Threshold Physical & Semantic Gate: Eliminates >98% of urban false alarms by coupling AI confidence with dB SPL/RMS energy thresholds.
  - Multimodal Warnings: High-contrast Rider HUD color flashing and Web Vibration API haptics.

---

### Slide 4: Verification, Benchmarks & Field Readiness
* **Title:** Engineering Rigor & Measured Benchmarks
* **Key Performance Indicators:**
  - **AI Inference Latency:** 14-18 ms on ARM Cortex / standard CPU (target: < 65 ms).
  - **Looming Onset Reaction:** < 80 ms from transient audio onset to haptic trigger.
  - **Memory Footprint:** < 45 MB RAM (90% reduction vs full TensorFlow).
  - **System Safety States:** Continuous monitoring across HEALTHY, DEGRADED, and UNAVAILABLE states to prevent silent failures.
* **Privacy by Design:** Zero Raw Audio Storage (RAM-only 0.975s ring buffer, no audio recorded to disk, compliant with Decree 13/2023/ND-CP).

---

### Slide 5: Roadmap, Feasibility & Business Value
* **Title:** From 0 VND MVP to Commercial Smart Mobility
* **Phase 1 (Current):** 100% Software-First Web & Mobile MVP with Web Haptics.
* **Phase 2 (Hardware Add-on Kit):**
  - Modular ESP32-S3 handlebar pod with 3-MEMS digital microphone array, USB Audio Class 2.0 (UAC2), and dual LRA haptic grips.
  - Total estimated BOM cost: ~950,000 VND (~1,550,000 VND fully assembled).
* **B2B / B2G Integration:**
  - Ready for integration with electric motorbike fleets (Dat Bike, VinFast) and urban mobility platforms.
  - Sustainable social impact for disability inclusion in smart cities.
