# 🌀 CycloneShield AI

**Agentic AI-based Cyclone Detection & Early Warning System for Coastal India**

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.45+-red)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 🎯 What It Does

CycloneShield AI is an agentic AI system that monitors weather data, detects cyclone threats, and generates impact assessments for coastal India using a pipeline of three specialized AI agents powered exclusively by **IBM watsonx.ai**.

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

## 🚀 Quick Start (5 minutes)

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/cycloneshield-ai.git
cd cycloneshield-ai
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment (optional for demo mode)

```bash
cp .env.example .env
# Edit .env if you want real LLM responses (IBM watsonx.ai credentials)
# Leave APP_MODE=demo to run without any API keys
```

### 4. Run the dashboard

```bash
python -m streamlit run app.py
```

Open your browser at **http://localhost:8501**

---

## 🔑 API Key Configuration

CycloneShield AI works in **demo mode without any API keys**. To enable real AI analysis with IBM watsonx.ai:

| Credential | Environment Variable | Notes |
|------------|---------------------|-------|
| IBM watsonx.ai API Key | `IBM_GRANITE_API_KEY` | From [IBM Cloud](https://cloud.ibm.com) |
| IBM watsonx.ai Project ID | `IBM_GRANITE_PROJECT_ID` | Your watsonx project GUID |
| IBM watsonx.ai URL | `IBM_GRANITE_URL` | Default: `https://us-south.ml.cloud.ibm.com` |

Edit your `.env` file:
```env
IBM_GRANITE_API_KEY=your_ibm_api_key_here
IBM_GRANITE_PROJECT_ID=your_ibm_project_id_here
IBM_GRANITE_URL=https://us-south.ml.cloud.ibm.com
PRIMARY_LLM_PROVIDER=granite
APP_MODE=live
```

> **IBM model selection**: Model configuration (`IBM_GRANITE_MODEL`) will be set separately as required. No model is hardcoded — the model ID is passed via environment variable or configuration.

---

## 📊 Dashboard Sections

1. **Overview** — Pipeline status, alert level, key metrics
2. **Weather Intelligence** — Pressure trends, wind charts, anomalies
3. **Cyclone Detection** — Storm detection, intensity, landfall assessment
4. **Cyclone Tracking** — Interactive Folium map with track visualization
5. **Impact Assessment** — Affected districts, risk levels, storm surge estimates
6. **Early Warning** — Alert status, preparedness checklist, emergency contacts
7. **Multi-Agent Activity** — Execution timeline, agent-to-agent communication log
8. **Human Verification** — Operator approval gate before alert is verified
9. **Model Evaluation** — Latency, token usage, completeness scores
10. **Settings** — API key status, guardrails information

---

## 🧪 Running Tests

```bash
python -m pytest tests/ -v
```

Expected: **51 tests pass**

---

## 🛡️ Safety & Responsible AI

- ✅ All AI outputs clearly labelled (demo / sample / live)
- ✅ AI **never** issues official government warnings
- ✅ Human-in-the-loop approval required before alert verification
- ✅ Prompt injection protection
- ✅ Output schema validation
- ✅ IMD contact always displayed with AI outputs
- ✅ API keys stored in `.env` only — never in code

---

## 🌐 Deployment

### Render (recommended)

1. Push to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your repository
4. Add IBM watsonx.ai environment variables in Render dashboard
5. Deploy

The `render.yaml` file is pre-configured.

### Local Production

```bash
python -m streamlit run app.py --server.port 8080 --server.address 0.0.0.0
```

### Windows

```powershell
python -m streamlit run app.py
```

---

## 📁 Project Structure

```
cycloneshield-ai/
├── app.py                    # Main Streamlit application
├── agents/
│   ├── weather_agent.py      # Agent 1: Weather Intelligence
│   ├── cyclone_agent.py      # Agent 2: Cyclone Detection & Tracking
│   └── impact_agent.py       # Agent 3: Impact Assessment & Early Warning
├── orchestration/
│   └── coordinator.py        # Sequential pipeline coordinator
├── providers/
│   ├── base.py               # Abstract LLM provider interface
│   ├── factory.py            # Provider selection logic (IBM only)
│   ├── demo_provider.py      # Demo mode (no API required)
│   └── granite.py            # IBM watsonx.ai provider
├── tools/
│   ├── weather_tools.py      # Weather data loading & validation
│   └── cyclone_tools.py      # Cyclone track loading & risk scoring
├── data/
│   ├── sample_weather.csv    # Bay of Bengal sample weather data
│   └── sample_cyclone_track.csv  # Sample cyclone track (Cyclone AGNI)
├── dashboard/
│   └── components.py         # Charts, maps, UI components
├── utils/
│   ├── validators.py         # Input/output validation + injection detection
│   └── logging_config.py     # Execution log & agent timer
├── tests/
│   └── test_cycloneshield.py # Automated tests
├── .env.example              # Environment variable template
├── requirements.txt
├── pytest.ini
├── render.yaml               # Render deployment config
└── README.md
```

---

## 🏆 Requirements Checklist

| Requirement | Status |
|-------------|--------|
| Working Agentic AI application | ✅ |
| Interactive Streamlit dashboard | ✅ |
| Three specialized AI agents | ✅ |
| IBM watsonx.ai integration | ✅ (only LLM provider; demo if no key) |
| Agent orchestration | ✅ Sequential pipeline |
| Agent-to-agent communication | ✅ Each agent receives prior agent output |
| Weather and cyclone data analysis | ✅ |
| Cyclone track visualization | ✅ Folium map |
| Impact assessment | ✅ |
| Preparedness recommendations | ✅ |
| Agent memory | ✅ Session-level AnalysisSession |
| Observability and execution logs | ✅ Full agent timeline |
| LLM evaluation | ✅ Latency, tokens, completeness |
| Guardrails | ✅ Injection detection, schema validation |
| Human-in-the-loop | ✅ Required before alert verification |
| Secure API key management | ✅ .env only, never hardcoded |
| Demo mode | ✅ Fully working without any API keys |
| Automated tests | ✅ |
| Deployment-ready | ✅ render.yaml included |

---

## ⚠️ Data Disclaimer

All sample data in `data/` is based on historical Bay of Bengal cyclone patterns (not real-time). The system clearly labels all outputs as SAMPLE, LIVE, or DEMO. This tool provides **decision support only** and does not issue official government warnings.

**For real cyclone information:**
- IMD: 1800-180-1717 | mausam.imd.gov.in
- NDMA: 011-26701700 | ndma.gov.in
