# NutriBin Backend

Backend service for NutriBin — a smart compost monitoring system that uses IoT + ML + rule-based intelligence to track compost conditions, detect anomalies, and generate real-time insights.

## Overview

NutriBin Backend processes sensor data and converts it into actionable intelligence:

- Tracks compost environmental conditions in real time
- Detects abnormal sensor behavior (hardware or process issues)
- Predicts compost stage progression
- Estimates remaining composting time using hybrid logic


## Tech Stack

- Python 3.11+
- FastAPI
- SQLAlchemy
- SQLite
- ML: Isolation Forest (Anomaly Detection)


## Core Modules

- **Stage Classification Engine** → rule-based compost stage detection (Start / Curing / Ready)
- **Time Prediction Engine** → hybrid model using trend analysis + heuristics
- **Anomaly Detection Engine** → Isolation Forest for detecting abnormal sensor patterns
- **Backend API Layer** → FastAPI-based real-time data handling


## Run Locally

### 1. Create virtual environment
```bash
python -m venv .venv
```

### 2. Activate environment
```bash
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Start server
```bash
uvicorn app.main:app --reload
```

### 5. Open API docs
```
http://127.0.0.1:8000/docs
```

## Project Goal

To build a real-time intelligent compost monitoring backend that can:

- Reduce manual compost monitoring effort
- Detect system or environmental anomalies early
- Provide predictive insights for compost completion
- Support scalable IoT-based environmental tracking systems
