<div align="center">

# 🛰️ KrishiPulse AI // Orbital Agro-Telemetry & Supply Console
### **Unified 4-Pillar Autonomous Agricultural Intelligence, Smart Micro-Grid & Supply-Chain Swarm**

[![Live Demo](https://img.shields.io/badge/LIVE_DEPLOYMENT-STREAMLIT_CLOUD-10B981?style=for-the-badge&logo=streamlit&logoColor=white)](https://krishipulseai-8qn2lphajzjdwfzcbuyu45.streamlit.app/)
[![GitHub Repo](https://img.shields.io/badge/SOURCE_CODE-GITHUB_REPO-0EA5E9?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Tanaygen/krishipulse_ai)
[![Python 3.11+](https://img.shields.io/badge/PYTHON-3.11%2B-F59E0B?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Gemini AI](https://img.shields.io/badge/ENGINE-GOOGLE_GEMINI_GENAI-A855F7?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![Zero Mock Data](https://img.shields.io/badge/COMPLIANCE-100%25_LIVE_TELEMETRY-14B8A6?style=for-the-badge)](#%EF%B8%8F-zero-dummy-data-verification)

**Built for NxtWave FORGE '26 Buildathon** by **Team Genius**  
*National Institute of Technology (NIT) Andhra Pradesh — Department of Computer Science & Engineering*

[🚀 **Launch Live App**](https://krishipulseai-8qn2lphajzjdwfzcbuyu45.streamlit.app/) • [📐 **System Architecture**](#-system-architecture) • [⚡ **4-Pillar Capabilities**](#-the-4-pillar-unified-engine) • [📱 **2G Watchdog & Mobile Turbo**](#-rural-2g-watchdog--mobile-edge-resilience) • [💻 **Local Setup**](#-local-installation--quickstart)

</div>

---

## 🌍 Overview

**KrishiPulse AI** is a real-time, zero-mock-data agricultural command system engineered to bridge orbital satellite telemetry and last-mile rural execution. By entering any Indian village, town, or district, the autonomous agent orchestrates four live physical and economic layers in a single pass:

1. **Pillar 01 — Auto-State Trilingual Voice Studio:** Resolves live GPS coordinates, detects the farmer's state, and synthesizes downloadable `.mp3` voice advisories in the **Local State Language** (Telugu, Marathi, Tamil, Kannada, Punjabi, Bengali, Gujarati, etc.) alongside **Hindi** and **English**.
2. **Pillar 02 — 3D WebGL Root-Zone Soil Core & Yield Shield:** Queries live `3–9 cm` root-zone soil moisture ($\text{m}^3/\text{m}^3$), `6 cm` soil temperature, and 7-day **FAO-56 Penman-Monteith Evapotranspiration ($\text{ET}_0$)** to compute exact pump runtime hours, protect harvest revenue ($\text{INR}$), and prevent urea washout before heavy rain.
3. **Pillar 03 — Smart Solar Micro-Grid & Transformer Controller:** Tracks 24-hour live shortwave solar irradiance ($\text{W/m}^2$) to schedule irrigation during peak photovoltaic generation while shifting pump loads away from `18:00–22:00` rural feeder transformer peaks.
4. **Pillar 04 — OSRM Highway Supply-Chain Swarm & SQLite Ledger:** Calculates real road distance and transit ETA over the **Open Source Routing Machine (OSRM)** highway network to the nearest regional APMC/Agri-Hub, automatically rerouting around flood hazards and logging immutable dispatches into a local **SQLite** ledger (`krishipulse_swarm.db`).

---

## 📐 System Architecture

```mermaid
flowchart TD
    User["👨‍🌾 Farmer / Operator (Desktop or Low-End Mobile)"] --> Watchdog{"⏱️ Client-Side Watchdog Probe\n(<2800ms / 2G / RTT Check)"}
    
    Watchdog -- "Fast Network / Desktop" --> Full3D["🛰️ Full 3D Orbital Mode\n(Three.js WebGL Soil Core + Esri Satellite Map + Plotly)"]
    Watchdog -- "Slow 2G / High RTT" --> Turbo3D["⚡ 3D Vector Turbo Mode\n(18 KB Inline 3D Isometric SVGs • 96% Payload Stripped)"]

    Full3D & Turbo3D --> Agent["🧠 Gemini Multi-Model Failover Router (agent.py)"]

    Agent --> T1["📍 Tool 1: Geocoding & Auto-State Router\n(Open-Meteo / Nominatim OSM API)"]
    Agent --> T2["🌱 Tool 2: Satellite Soil & FAO-56 Yield Engine\n(3-9cm Moisture, 6cm Temp, 7d Rain & ET0)"]
    Agent --> T3["☀️ Tool 3: Smart Solar Micro-Grid Controller\n(24h Shortwave Irradiance W/m² & Feeder Load)"]
    Agent --> T4["🚚 Tool 4: OSRM Highway Logistics Swarm\n(Live Road Vector + SQLite Dispatch Ledger)"]

    T1 & T2 & T3 & T4 --> Voice["🔊 Trilingual Voice Synthesizer (gTTS)\nRegional Language + Hindi + English (.mp3)"]