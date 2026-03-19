# PS4 — Predictive Customer Outreach & Churn Prevention
### Union Bank of India · iDEA Hackathon 2.0 · 2026

A full-stack AI-powered churn prevention system with:
- 🤖 ML churn prediction (XGBoost + SHAP)
- ✨ Gen-AI personalised messages (Claude API)
- 📡 Multi-channel outreach simulation
- 📊 Real-time analytics dashboard

---

## Project Structure

```
ps4_churn_system/
├── app.py                    ← FastAPI backend (main entry point)
├── requirements.txt
├── data/
│   └── generate_data.py      ← Synthetic customer data generator
├── ml/
│   └── churn_model.py        ← XGBoost model + SHAP scoring
├── ai/
│   └── message_generator.py  ← Claude API message generation
├── outreach/
│   └── channel_simulator.py  ← Multi-channel dispatch simulator
└── static/
    └── index.html            ← Full dashboard UI
```

---

## Setup & Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your Claude API key
```bash
# Linux / Mac
export ANTHROPIC_API_KEY=your_api_key_here

# Windows (CMD)
set ANTHROPIC_API_KEY=your_api_key_here
```

### 3. Start the server
```bash
cd ps4_churn_system
python app.py
```

### 4. Open the dashboard
```
http://localhost:8000
```

---

## What Happens on First Load

1. **300 synthetic bank customers** are generated automatically
2. **XGBoost model** is trained on this data and saved
3. **Churn scores** (0–1) are computed for all customers
4. **SHAP-based** top 3 churn reasons extracted per customer
5. **Dashboard** loads with KPIs, charts, and at-risk customer table

---

## Features by Tab

| Tab | Description |
|-----|-------------|
| 📊 Overview | KPI tiles, segment charts, city heatmap |
| 👥 At-Risk Customers | Scored customer table with filters |
| ✉️ AI Messages | Claude-powered personalised message generator |
| 📡 Outreach | Campaign simulation with live dispatch log |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard` | KPIs, segment stats, charts data |
| GET | `/api/customers` | List scored customers (filterable) |
| GET | `/api/customers/{id}` | Single customer detail |
| POST | `/api/generate-message/{id}` | Generate AI message via Claude |
| POST | `/api/send-outreach/{id}` | Simulate channel dispatch |
| POST | `/api/run-campaign?limit=N` | Run full campaign on top N customers |
| GET | `/api/outreach-log` | View dispatch history |
| POST | `/api/reset` | Reset all state |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| ML Model | XGBoost + scikit-learn |
| Explainability | Rule-based SHAP proxy |
| Gen-AI | Claude API (claude-sonnet) |
| Backend | FastAPI + Python |
| Frontend | Vanilla HTML/CSS/JS + Chart.js |
| Data | Synthetic (pandas + numpy) |
