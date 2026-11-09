# 🌀 CycloneShield AI

**Agentic AI-based Cyclone Detection & Early Warning System for Coastal India**

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.45+-red)](https://streamlit.io)
[![IBM Granite](https://img.shields.io/badge/IBM-granite--4--h--small-blue)](https://ibm.com/watsonx)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 🎯 What It Does

CycloneShield AI is an agentic AI system that monitors weather data, detects cyclone threats, and generates impact assessments for coastal India using a pipeline of three specialized AI agents powered by **IBM watsonx.ai Granite 4 H Small** (`ibm/granite-4-h-small`).

### Operating Modes

| Mode | When Active | What it means |
|------|-------------|----------------|
| **🟢 LIVE AI** | IBM credentials configured, `APP_MODE` not set to `demo` | Real IBM Granite AI responses via watsonx.ai |
| **🔵 DEMO** | No credentials, or `APP_MODE=demo` | Pre-written synthetic responses, clearly labelled |

The application **never** labels demo/simulated results as real AI results. The dashboard shows the active mode, model ID, and data source prominently on every page.

### Three Specialized Agents

| Agent | Role | LLM Task |
|-------|------|----------|
| **Weather Intelligence Agent** | Analyzes meteorological data from Bay of Bengal stations | Detects pressure drops, wind anomalies, humidity spikes |
| **Cyclone Detection & Tracking Agent** | Examines cyclone patterns and track data | Identifies intensity, movement, landfall risk |
| **Impact Assessment & Early Warning Agent** | Evaluates coastal impacts | Generates preparedness guidance, risk levels |

### Sequential Agent Pipeline

```
Weather Data → [Weather Agent] → [Cyclone Agent] → [Impact Agent] → Human Review → Dashboard
```

---

## 🚀 Quick Start — Streamlit (Local)

### ⚠️ Python Version Requirement

`ibm-watsonx-ai` (IBM Granite SDK) requires **Python 3.11–3.14**. It does **NOT** work with Python 3.15+.
This project includes a `.venv` with Python 3.13 and all dependencies pre-installed.

### 1. Install dependencies into the .venv

```powershell
# Use the .venv Python (3.13) — NOT the system Python:
.\.venv\Scripts\pip install -r requirements-local.txt
```

### 2. Configure environment

```powershell
Copy-Item .env.example .env
# Edit .env — see "Live AI Setup" below, or leave APP_MODE=demo for demo mode
```

### 3. Run the Streamlit dashboard (port 8503)

```powershell
# CORRECT — uses .venv Python 3.13 with ibm-watsonx-ai:
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8503

# Or use the included launcher:
run.bat        # Windows CMD
.\run.ps1      # PowerShell

# INCORRECT — uses system Python 3.15 which CANNOT import ibm-watsonx-ai:
# streamlit run app.py    ← DO NOT USE THIS
```

Open your browser at **http://localhost:8503**

The dashboard title bar shows **🟢 LIVE AI MODE** or **🔵 DEMO MODE** so you always know which mode is active.

---

## 🤖 Live AI Setup (IBM Granite 4 H Small)

### What you need

| Credential | Environment Variable | Where to get it |
|------------|---------------------|-----------------|
| IBM API Key | `IBM_GRANITE_API_KEY` | [cloud.ibm.com](https://cloud.ibm.com) → Manage → IAM → API keys → Create |
| Project ID | `IBM_GRANITE_PROJECT_ID` | [us-south.dataplatform.cloud.ibm.com](https://us-south.dataplatform.cloud.ibm.com) → Your project → Manage |
| Watson URL | `IBM_GRANITE_URL` | Default: `https://us-south.ml.cloud.ibm.com` (no change needed for us-south) |

### Setup steps

```powershell
# 1. Copy the example
Copy-Item .env.example .env

# 2. Edit .env and replace placeholders:
#    IBM_GRANITE_API_KEY=your_actual_ibm_api_key
#    IBM_GRANITE_PROJECT_ID=your_actual_project_id

# 3. IMPORTANT: Remove or comment out APP_MODE=demo in .env
#    (having APP_MODE=demo overrides the credentials and forces demo mode)

# 4. Run
python -m streamlit run app.py
```

When Live AI mode is active, the dashboard shows:
- 🟢 **LIVE AI MODE** — IBM Granite (ibm/granite-4-h-small)
- Weather data source (Open-Meteo live or sample CSV)
- Each page shows which model generated the analysis

### How mode is determined

```
IBM_GRANITE_API_KEY set AND non-placeholder
IBM_GRANITE_PROJECT_ID set AND non-placeholder
APP_MODE != "demo"
─────────────────────────────────────────────
→ 🟢 LIVE AI MODE (ibm/granite-4-h-small)

Otherwise:
→ 🔵 DEMO MODE (pre-written responses)
```

> **Live AI confirmation:** The system only claims Live AI mode is active after successfully receiving a real response from `ibm/granite-4-h-small` via the IBM watsonx.ai SDK (`ibm-watsonx-ai >= 1.9.1`, Python 3.13, using the Chat API). If the credentials are present but the API returns an error (invalid key, rate limit, model access denied), the error is shown clearly — the system does NOT silently fall back to demo while claiming to be live.
>
> **API used:** `ibm/granite-4-h-small` is a chat model. The provider calls `ModelInference.chat(messages=[...])` which returns `{"choices": [{"message": {"content": "..."}}], "usage": {...}}`. NOT `generate_text()`.

---

## 🌦️ Live Weather Data

Real weather is fetched from **Open-Meteo** (free, no API key required) for 8 Bay of Bengal coastal stations:
Chennai, Visakhapatnam, Bhubaneswar, Puri, Gopalpur, Kolkata, Port Blair, Paradip.

| Source | Requires | Data type |
|--------|----------|-----------|
| **Open-Meteo** | Nothing (free) | Real surface pressure, wind, humidity, precipitation |
| **OpenWeatherMap** | `OPENWEATHER_API_KEY` | Real current conditions (optional) |
| **Sample CSV** | Nothing | Illustrative historical data (fallback if live APIs fail) |

The data source is always shown in the dashboard (`live (Open-Meteo)`, `sample (CSV)`, etc.).

> **Cyclone track data** is still sample/illustrative (CSV). There is no free real-time cyclone track API integrated. The AI analysis via Granite is real; the track coordinates it analyses are from the sample dataset.

---

## 🧪 Running Tests

```powershell
python -m pytest tests/ -v
```

**Expected: 83 tests pass** (no API keys required — all tests use demo mode or mock providers).

### Test coverage

| Test class | What it covers |
|------------|----------------|
| `TestValidators` | Input validation, injection detection, JSON extraction |
| `TestWeatherTools` | Sample data loading, validation, data source labels |
| `TestCycloneTools` | Track loading, risk scoring |
| `TestDemoProvider` | Pre-written responses, JSON validity |
| `TestWeatherAgent` | Agent pipeline, fallback, injection blocking |
| `TestCycloneAgent` | Cyclone detection, no-track handling |
| `TestImpactAgent` | Risk assessment, official disclaimer, alert level |
| `TestOrchestrator` | Full pipeline, human review, session memory |
| `TestLogging` | Execution log, agent timer |
| **`TestModeSelection`** | **Live vs demo mode selection, credential detection** |
| **`TestGraniteProvider`** | **Model ID, credential validation, error responses** |
| **`TestLiveDemoDistinction`** | **is_demo flag, session ai_mode, data labels** |
| **`TestLiveWeatherTools`** | **data_source fields, Open-Meteo label, hardcoded fallback** |
| **`TestAPIFailureHandling`** | **API errors do not fall back silently to demo** |

---

## 📡 API Contract (Vercel serverless)

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `/api/health` | GET | — | `{status, mode, providers, version}` |
| `/api/weather` | GET | `?live=false` | `{readings[], count, source}` |
| `/api/track` | GET | `?storm_id=` | `{track[], count, source}` |
| `/api/analyze` | POST | `{location?, provider_override?, use_live_weather?}` | Full `AnalysisSession` JSON |
| `/api/review` | POST | `{session_data, decision, reviewer, notes?}` | `{human_review_status, status, reviewer, timestamp}` |

---

## 💻 Local Full-Stack Development (Next.js + Python API)

Terminal 1 — Python API server:
```powershell
python dev_server.py
# API running at http://localhost:8000
```

Terminal 2 — Next.js frontend:
```powershell
cd frontend
npm install
npm run dev
# UI running at http://localhost:3000
```

Open http://localhost:3000 — the frontend proxies `/api/*` to `localhost:8000`.

---

## 🌐 Deployment

### Vercel (Next.js frontend + Python serverless API)

The Vercel deployment uses **two independent Vercel projects** pointing at the same GitHub repository:

| Vercel project | Root Directory | What it deploys |
|----------------|----------------|-----------------|
| **Frontend** | `frontend` | Next.js 16 app (all 10 dashboard pages) |
| **Backend** | *(repo root)* | Python serverless functions in `api/` |

**Backend project environment variables for Vercel:**
- `APP_MODE` = `demo` (Vercel deployment runs demo mode by default — the IBM SDK is too large for the bundle limit)
- To enable live AI on Vercel: add `IBM_GRANITE_API_KEY` and `IBM_GRANITE_PROJECT_ID` and add `ibm-watsonx-ai` to `requirements.txt`

> **Vercel note:** `requirements.txt` intentionally excludes `ibm-watsonx-ai` (~100 MB) to stay within Vercel's 250 MB bundle limit. The local Streamlit app uses `requirements-local.txt` which includes the full SDK.

---

## 📁 Project Structure

```
cycloneshield-ai/
├── app.py                       # Streamlit application (local)
├── dev_server.py                # Local Python API dev server
├── vercel.json                  # Vercel deployment configuration
├── requirements.txt             # Lean backend deployment deps (Vercel)
├── requirements-local.txt       # Full local/Streamlit deps (incl. IBM Granite SDK)
│
├── api/                         # Vercel Python serverless functions
│   ├── health.py                # GET  /api/health
│   ├── weather.py               # GET  /api/weather
│   ├── track.py                 # GET  /api/track
│   ├── analyze.py               # POST /api/analyze (full pipeline)
│   └── review.py                # POST /api/review (human verification)
│
├── frontend/                    # Next.js 16 application
│   ├── package.json
│   ├── next.config.js
│   └── app/components/          # 10 dashboard pages
│
├── agents/
│   ├── weather_agent.py         # Agent 1: Weather Intelligence
│   ├── cyclone_agent.py         # Agent 2: Cyclone Detection & Tracking
│   └── impact_agent.py          # Agent 3: Impact Assessment & Early Warning
│
├── orchestration/
│   └── coordinator.py           # Sequential pipeline coordinator
│                                # (ai_mode, data_mode, data_source_label tracked)
│
├── providers/
│   ├── base.py                  # Abstract LLM provider interface (LLMResponse)
│   ├── factory.py               # Provider selection + get_provider_mode()
│   ├── demo_provider.py         # Demo mode (pre-written responses, is_demo=True)
│   └── granite.py               # IBM watsonx.ai (ibm/granite-4-h-small)
│
├── tools/
│   ├── weather_tools.py         # Weather loading: Open-Meteo → OWM → sample CSV
│   └── cyclone_tools.py         # Cyclone track loading & risk scoring
│
├── data/
│   ├── sample_weather.csv       # Bay of Bengal sample weather data
│   └── sample_cyclone_track.csv # Sample cyclone track (Cyclone AGNI)
│
├── dashboard/
│   └── components.py            # Streamlit charts, maps, UI components
│
├── utils/
│   ├── validators.py            # Input/output validation + injection detection
│   └── logging_config.py        # Execution log & agent timer
│
└── tests/
    └── test_cycloneshield.py    # 83 automated tests
```

---

## 🛡️ Safety & Responsible AI

- ✅ All AI outputs clearly labelled (demo / sample / live AI)
- ✅ **Live AI mode never claimed unless a real Granite response was received**
- ✅ **Demo mode never disguised as Live AI**
- ✅ AI **never** issues official government warnings
- ✅ Human-in-the-loop approval required before alert verification
- ✅ Prompt injection protection on all agent inputs
- ✅ Output JSON schema validation
- ✅ IMD emergency contact always displayed with AI outputs
- ✅ API keys stored in `.env` only — never in code or frontend
- ✅ API keys never appear in log messages or error responses

---

## 🔧 Troubleshooting

### "ibm-watsonx-ai SDK not installed" error in the dashboard

**Root cause:** You are running Streamlit with the wrong Python interpreter (Python 3.15). `ibm-watsonx-ai` requires Python <3.15.

**Fix:**
```powershell
# Use the .venv interpreter explicitly:
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8503

# Or run the included launcher:
run.bat        # Windows CMD
.\run.ps1      # PowerShell
```

### Dashboard shows DEMO mode even with credentials configured

Check these in order:
1. Is `APP_MODE=demo` set in your `.env`? If so, remove or change to `APP_MODE=live`.
2. Are `IBM_GRANITE_API_KEY` and `IBM_GRANITE_PROJECT_ID` set to non-placeholder values?
3. Are you using the `.venv` interpreter? (See above)
4. Go to **Settings → Test IBM Granite Connectivity** to run a live test.

### Port 8501 vs 8503

The default port is now **8503** (configured in `.streamlit/config.toml`). Always use:
```
http://localhost:8503
```

---

## ⚠️ Known Limitations

| Limitation | Details |
|-----------|---------|
| **No live cyclone track API** | Cyclone track data is from sample CSV. Real-time IMD track data requires a paid/authorized API not publicly available. |
| **AI responses not verified meteorologically** | Granite AI is a general-purpose language model, not a certified meteorological system. All outputs are decision-support only. |
| **IBM Granite availability** | `ibm/granite-4-h-small` access requires an IBM watsonx.ai account with the model enabled. If the model is unavailable, the error is shown clearly. |
| **Python version constraint** | `ibm-watsonx-ai` requires Python 3.11–3.14. The `.venv` (Python 3.13) is correctly configured. The system Python 3.15 cannot install the SDK. |
| **Vercel deployment uses demo mode** | The IBM SDK size makes it impractical for Vercel serverless; local Streamlit uses the full SDK. |
| **Live weather: no SST** | Open-Meteo provides surface pressure, wind, temperature, humidity, and precipitation. Sea surface temperature requires a different API. |

---

## ⚠️ Data Disclaimer

All sample data in `data/` is **illustrative only** — it is based on historical Bay of Bengal cyclone patterns and does **not** represent live or current cyclone warnings. Demo mode outputs are synthetic and are provided for testing and demonstration only. This tool provides **decision support only** and does not issue official government warnings.

**For real cyclone information:**
- IMD: **1800-180-1717** | [mausam.imd.gov.in](https://mausam.imd.gov.in)
- NDMA: **011-26701700** | [ndma.gov.in](https://ndma.gov.in)
- INCOIS: [incois.gov.in](https://incois.gov.in)
