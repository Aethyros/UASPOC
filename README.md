# UASPOC

> **Simulation Notice:** This repository contains a software-based Proof of Concept (PoC) simulator developed for internal airspace defense research. All capabilities — including multi-modal sensor ingestion, RF signal intelligence, AI classification, trajectory tracking, threat assessment, and cyber takeover execution — are purely mathematical simulations. This software does not perform real-world RF interception, physical transmission, or live UAV engagement.

---

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [System Architecture](#system-architecture)
- [Simulated Threat Profiles](#simulated-threat-profiles)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)

---

## Overview

This platform provides an integrated, real-time software simulation pipeline for validating multi-modal UAV threat detection, AI-driven classification, continuous spatial tracking, and non-kinetic countermeasure execution. It is designed as a modular, production-grade proof of concept to accelerate research and development of next-generation counter-UAS systems.

---

## Problem Statement

The proliferation of commercially available UAVs has significantly outpaced the development of effective detection and neutralization technologies. While drones offer substantial utility, their growing accessibility introduces serious security risks in contested airspace — from unauthorized surveillance and payload delivery to targeted kinetic threats.

Current airspace defense infrastructure faces several critical limitations:

**Detection Failures**
Traditional radar systems struggle to reliably identify small, low-altitude UAVs due to their minimal radar cross-section and low-altitude flight paths.

**Unsafe Neutralization Methods**
Broad-spectrum RF jamming — the most common neutralization tactic — does not guarantee controlled descent. It frequently causes rogue UAVs to crash unpredictably into civilian infrastructure.

**Prohibitive Deployment Costs**
Comprehensive solutions combining high-confidence detection, AI classification, and surgical cyber takeover capabilities remain cost-prohibitive for rapid prototyping and iterative testing.

This platform directly addresses these gaps through a decoupled, sequentially-pipelined simulation environment.

---

## System Architecture

The platform is structured as five standalone, concurrently-operating functional modules connected via REST API contracts. Each module owns a discrete processing stage, enabling parallel development and clean system boundaries.

| # | Module | Owner | Responsibility |
|---|--------|-------|----------------|
| 1 | RF Detection & Signal Intelligence | Abhishek Bhadani | Synthesizes raw RF wave data across 2.4 GHz, 5.8 GHz, and 900 MHz spectrums; manages the PostgreSQL signature database; executes rule-based protocol identification (DJI Lightbridge, MAVLink). |
| 2 | Signal Processing & Telemetry Analytics | Bhavya Agrawal | Applies FFT transformations via SciPy to extract frequency-domain features; renders 128×128 PNG spectrogram artifacts; generates structured telemetry streams. |
| 3 | AI Detection & Drone Classification | Sugapriyan S | Consumes RF spectrograms and simulated optical/thermal video frames; classifies targets by UAV type, make, model, and payload capabilities using YOLOv8-Small (TensorRT-accelerated). |
| 4 | Airspace Simulation, Tracking & Prediction | Prathamesh Kapase | Maintains continuous target locks using Kalman Filters and DeepSORT multi-object tracking; extrapolates flight trajectories and computes optimal intercept vectors. |
| 5 | Sensor Fusion, Mission Control & Decision Engine | Sumedh Bhat | Aggregates all multi-modal streams, cross-references RF fingerprints against visual classifications, computes dynamic threat scores, and initiates non-kinetic countermeasures against confirmed hostile targets. |

---

## Simulated Threat Profiles

The PostgreSQL database provides ground-truth reference profiles evaluated against incoming synthetic signals during simulation runs.

| Target Model | Center Frequency | Bandwidth | Protocol |
|:---|:---|:---|:---|
| DJI Phantom 4 | 2.400 GHz | 20 MHz | DJI Lightbridge (proprietary, ≤ 25 MHz) |
| Generic Custom FPV | 5.800 GHz | 40 MHz | Generic Analog / Digital RC Link (5.7–5.9 GHz) |
| Parrot Bebop | 2.410 GHz | 15 MHz | MAVLink Telemetry (900 MHz / 2.4 GHz) |

---

## Technology Stack

| Layer | Technologies |
|:---|:---|
| Core Language & Orchestration | Python 3.x, FastAPI, Uvicorn |
| Signal Synthesis & Processing | NumPy, SciPy, Matplotlib |
| AI & Computer Vision |  |
| Database | PostgreSQL, psycopg2 |
| Frontend | React.js, Figma (UI mockups), PlantUML (architecture diagrams) |

---

## Repository Structure

Each developer is exclusively assigned to their designated subdirectory under `src/`. Do not modify files outside your assigned module.

```
counter-uas-prototype/
│
├── .gitignore              
├── requirements.txt        # Core dependencies: fastapi, uvicorn, numpy, scipy,
│                           #   psycopg2, opencv-python, torch
├── README.md
│
└── src/
    ├── __init__.py
    ├── main.py
    ├── rf_intelligence/            # Owner: Abhishek Bhadani
    ├── signal_processing/          # Owner: Bhavya Agrawal
    ├── ai_detection/               # Owner: Sugapriyan S
    ├── airspace_tracking/          # Owner: Prathamesh Kapase
    └── mission_control/            # Owner: Sumedh Bhat
```

---

## Getting Started

### Prerequisites

- Python 3.x
- PostgreSQL (running locally)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/counter-uas-prototype/UASPOC.git
cd UASPOC

# 2. Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Running the Server

```bash
# Navigate into the source directory before launching
cd src

# Start the FastAPI development server
uvicorn main:app --reload
```

| Endpoint | URL |
|:---|:---|
| Master Switchboard | `http://127.0.0.1:8000/` |
| Interactive API Docs (Swagger UI) | `http://127.0.0.1:8000/docs` |

