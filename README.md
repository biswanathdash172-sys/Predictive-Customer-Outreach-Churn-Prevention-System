# 🏦 PS4 — Predictive Customer Outreach & Churn Prevention

<div align="center">

<img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
<img src="https://img.shields.io/badge/XGBoost-FF6600?style=for-the-badge&logo=xgboost&logoColor=white"/>
<img src="https://img.shields.io/badge/Claude_API-Sonnet-D4730A?style=for-the-badge&logo=anthropic&logoColor=white"/>
<img src="https://img.shields.io/badge/Chart.js-FF6384?style=for-the-badge&logo=chartdotjs&logoColor=white"/>
<img src="https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge"/>

<br/><br/>

> **ML Churn Prediction · GenAI Personalisation · Omni-Channel Outreach**

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [How It Works](#-how-it-works)
- [Features](#-features)
- [Customer Segments](#-customer-segments)
- [Project Structure](#-project-structure)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [Dashboard](#-dashboard)
- [API Reference](#-api-reference)
- [Churn Score Logic](#-churn-score-logic)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)

---

## 🎯 Overview

**PS4** is a two-part AI system that identifies bank customers likely to churn — up to **90 days in advance** — and automatically crafts hyper-personalised outreach messages delivered through the most effective channel at the optimal time.

| Engine | Technology | Role |
|---|---|---|
| 🤖 **ML Prediction** | XGBoost + SHAP | Scores every customer with a churn probability (0–1) and extracts top 3 churn reasons |
| ✨ **Gen-AI Messaging** | Claude API | Writes personalised retention messages tailored to each customer's segment, language, and churn behaviour |

```
Customer at Risk ──► ML Score ──► Segment ──► Claude AI Message ──► Right Channel ──► Offer Accepted
                                                                            │
                                                     Feedback Loop ◄────────┘
                                               (retrains model monthly)
```

---

## ⚙️ How It Works

The system runs as a continuous 8-stage pipeline:

<details>
<summary><b>Stage 1 — Data Collection & Feature Engineering</b></summary>

<br/>

Gathers customer features across four categories:

- **Transactions** — frequency, recency, average ticket size, product mix (last 12 months)
- **Digital engagement** — app logins, net banking sessions, days since last login
- **Product lifecycle** — loan repayment track, FD maturity dates, credit card utilisation
- **Competitive signals** — cross-bank fund outflows detected via NACH / UPI mandates

All features are normalised and stored for daily batch scoring.

</details>

<details>
<summary><b>Stage 2 — Churn Risk Scoring</b></summary>

<br/>

- **Model:** XGBoost / LightGBM trained on 24 months of historical churn labels
- **Outputs:** Churn probability (0–1), predicted churn horizon (30 / 60 / 90 days), top 3 churn reasons via SHAP
- **Clustering:** K-Means segments customers by churn reason type
- **Scheduling:** Scores refreshed daily via Apache Airflow DAG

| Score | Risk Tier | Action |
|---|---|---|
| `> 0.80` | 🔴 Critical | Immediate RM call + Active Outreach Queue |
| `0.65 – 0.80` | 🟠 High | Active Outreach Queue |
| `0.40 – 0.65` | 🟡 Medium | Watchlist |
| `< 0.40` | 🟢 Low | No action needed |

</details>

<details>
<summary><b>Stage 3 — Segmentation & Priority Ranking</b></summary>

<br/>

Customers are ranked using a **Priority Index**:

```
Priority Index = CLV Score × Churn Probability
```

- **High CLV + High Risk** → Relationship Manager (RM) personal outreach
- **Mid-tier** → Automated campaign engine

</details>

<details>
<summary><b>Stage 4 — Gen-AI Message Generation</b></summary>

<br/>

For every at-risk customer, Claude API generates two message variants (A/B test) using:

- Customer segment profile and churn reasons
- Product history and preferred language
- Bank tone guidelines and RBI compliance rules

Each message pair is reviewed by a **Compliance Checker prompt** before dispatch.

</details>

<details>
<summary><b>Stage 5 — Channel Selection & Dispatch</b></summary>

<br/>

Channel selected based on historical open/click data per customer:

```
WhatsApp (85% open) → Push Notification (62%) → SMS (78%) → Email (38%) → RM Call (70%)
```

- DND registry checked before every dispatch
- Optimal send-time predicted per customer

</details>

<details>
<summary><b>Stage 6 — Response Tracking</b></summary>

<br/>

Real-time event stream tracks: `Delivered → Opened → Clicked → Responded → Offer Accepted`

- No response in **72 hours** → auto-escalate to next channel
- Offer accepted → churn score reset to **0.10** + CRM updated

</details>

<details>
<summary><b>Stage 7 — Feedback Loop & Model Retraining</b></summary>

<br/>

- Actual churn outcomes recorded at 30 / 60 / 90 days
- True/False positive labels fed back into the training dataset
- Model retrained **monthly** with fresh features + SHAP drift detection
- A/B test results used to fine-tune Claude prompts

</details>

<details>
<summary><b>Stage 8 — Management Dashboard</b></summary>

<br/>

Live KPI dashboard with:

- Customers at risk, outreach sent, conversions, revenue saved
- Cohort analysis by segment, channel, and product type
- Branch-wise churn heatmap across geography
- RM leaderboard — who has the highest churn reversal rate

</details>

---

## ✨ Features

- 🔮 **90-Day Churn Forecasting** — predict churn 30, 60, or 90 days before it happens
- 🧠 **SHAP Explainability** — understand exactly why each customer is at risk
- 💬 **Segment-Aware AI Messages** — Claude generates different messages per churn reason
- ⚖️ **RBI Compliance Check** — every AI message validated before dispatch
- 📡 **Smart Channel Routing** — selects best channel per customer automatically
- 🔕 **DND Registry Compliance** — never messages opted-out customers
- ⏰ **Optimal Send-Time Prediction** — messages sent when each customer historically opens them
- 🔄 **Closed Feedback Loop** — real outcomes retrain the model monthly
- 📊 **Live Analytics Dashboard** — real-time KPIs, segment charts, city heatmaps

---

## 👥 Customer Segments

| Segment | Signal | Recommended Action | Best Channel |
|---|---|---|---|
| 💸 **Price-Sensitive** | Competitor UPI outflows, early FD withdrawal | Higher FD rate / zero-fee account upgrade | WhatsApp + RM Call |
| 😴 **Disengaged** | No app login 60+ days, zero transactions | Highlight unused features (UPI Lite, Sweep FD) | Push Notification |
| 🔄 **Life-Event** | Salary jump, new city, marriage-related spending | Pre-approved home loan or personal loan | Email + WhatsApp |
| 😠 **Complaint-Driven** | 3+ complaints, low CSAT, escalation history | Empathetic apology + dedicated RM + fee waiver | RM Call (priority) |
| 📦 **Product Maturity** | FD/RD maturing, loan fully repaid | Renewal offer or next product recommendation | SMS + Email |

---

## 📁 Project Structure

```
ps4_churn_system/
│
├── 📄 app.py                     # FastAPI backend — main entry point
├── 📄 requirements.txt           # Python dependencies
│
├── 📂 data/
│   └── generate_data.py          # Synthetic customer data generator (300 customers)
│
├── 📂 ml/
│   └── churn_model.py            # XGBoost training, scoring, SHAP reason extraction
│
├── 📂 ai/
│   └── message_generator.py      # Claude API — 2 message variants + compliance check
│
├── 📂 outreach/
│   └── channel_simulator.py      # Multi-channel dispatch simulator with realistic outcomes
│
└── 📂 static/
    └── index.html                # Full dashboard UI — Chart.js + 4-tab interface
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **ML Model** | XGBoost + scikit-learn | Churn probability scoring & CLV estimation |
| **Explainability** | SHAP | Top churn reason extraction per customer |
| **Clustering** | K-Means / HDBSCAN | Customer segment identification |
| **Gen-AI / LLM** | Claude API (`claude-sonnet`) | Personalised message generation + compliance check |
| **Backend** | FastAPI + Python | REST API, campaign engine, state management |
| **Data** | pandas + numpy | Synthetic data generation + feature engineering |
| **Frontend** | HTML + CSS + Vanilla JS | Dashboard UI (no framework dependencies) |
| **Charts** | Chart.js | Segment bar, risk tier doughnut, channel breakdown |
| **Web Server** | uvicorn | ASGI server for FastAPI |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+** — check with `python --version`
- **pip** — comes bundled with Python
- **Claude API Key** — get one free at [console.anthropic.com](https://console.anthropic.com)

### Step 1 — Clone & install

```bash
git clone https://github.com/your-username/ps4-churn-prevention.git
cd ps4-churn-prevention
pip install -r requirements.txt
```

### Step 2 — Set your API key

```bash
# macOS / Linux
export ANTHROPIC_API_KEY=your_api_key_here

# Windows (Command Prompt)
set ANTHROPIC_API_KEY=your_api_key_here

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="your_api_key_here"
```

> 💡 **No API key?** The system still runs fully — it uses fallback template messages instead of Claude AI-generated ones. Only the message generation step requires the key.

### Step 3 — Start the server

```bash
python app.py
```

You should see:

```
✅ Generated 300 synthetic customers → data/customers.csv
✅ Model trained | AUC: 0.891
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 4 — Open the dashboard

```
http://localhost:8000
```

> ⏱️ **First load takes ~15 seconds** — the system auto-generates data and trains the XGBoost model. All subsequent loads are instant.

---

## 🖥️ Dashboard

The dashboard has four tabs:

### 📊 Overview
Real-time KPI tiles, three analytics charts, and a city-wise churn heatmap.

| Tile | Description |
|---|---|
| Total Customers | All customers in the system |
| At Risk | Churn score > 0.65 |
| Critical | Churn score > 0.80 |
| Outreach Sent | Total messages dispatched |
| Conversions | Churn reversals (offer accepted) |
| Revenue Saved | Estimated CLV × conversion rate |

### 👥 At-Risk Customers
Full scored customer table sorted by Priority Index. Filter by risk tier or queue. Click **✉ Msg** on any row to jump to AI message generation for that customer.

### ✉️ AI Messages
1. Select an at-risk customer from the dropdown
2. Click **Generate Message** — Claude writes 2 personalised variants in ~3–5 seconds
3. See Variant A, Variant B, compliance result (PASS/FAIL), channel, and language
4. Click **Send Outreach** to simulate dispatch

### 📡 Outreach
Run full campaigns on top 10 / 20 / 50 at-risk customers. Live dispatch log shows every result: `Sent` · `Offer Accepted` · `DND Blocked`

---

## 🔌 API Reference

**Base URL:** `http://localhost:8000`  
**Interactive docs:** [`http://localhost:8000/docs`](http://localhost:8000/docs)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the dashboard HTML |
| `GET` | `/api/dashboard` | KPIs, segment stats, tier counts, city churn data |
| `GET` | `/api/customers` | Scored customers — supports `?tier=`, `?queue=`, `?limit=` |
| `GET` | `/api/customers/{id}` | Full profile for a single customer |
| `POST` | `/api/generate-message/{id}` | Generate AI message via Claude |
| `POST` | `/api/send-outreach/{id}` | Simulate channel dispatch |
| `POST` | `/api/run-campaign?limit=N` | Run full campaign on top N at-risk customers |
| `GET` | `/api/outreach-log` | Dispatch history with open/click/acceptance outcomes |
| `POST` | `/api/reset` | Clear all state and regenerate from scratch |

**Example — Generate a message**

```bash
curl -X POST http://localhost:8000/api/generate-message/UBI10023
```

```json
{
  "message_a": "Dear Priya, we noticed you haven't used your UBI app in a while...",
  "message_b": "Hi Priya! Your Fixed Deposit is eligible for a special renewal rate...",
  "compliance_ok": true,
  "compliance_note": "No mis-selling detected. RBI guidelines met.",
  "channel": "WhatsApp",
  "language": "English"
}
```

**Example — Run a campaign**

```bash
curl -X POST "http://localhost:8000/api/run-campaign?limit=20"
```

```json
{
  "total_sent": 20,
  "opened": 16,
  "clicked": 8,
  "accepted": 5,
  "open_rate": 80.0,
  "conversion_rate": 25.0
}
```

---

## 📊 Churn Score Logic

**Priority Index**
```
Priority Index = CLV Score × Churn Probability
```

**Revenue Saved Estimation**
```
Estimated Revenue Saved = Σ (CLV Score × 0.30) for each converted customer
```

**Channel Open Rates**

| Channel | Open Rate | Click Rate | Response Rate |
|---|---|---|---|
| WhatsApp | 85% | 42% | 28% |
| SMS | 78% | 22% | 12% |
| Push Notification | 62% | 30% | 18% |
| Email | 38% | 15% | 8% |
| RM Call | 70% | 55% | 45% |

---

## 🗺️ Roadmap

| Feature | Status |
|---|---|
| PostgreSQL for persistent storage | 🔜 Planned |
| Apache Airflow daily scoring DAG | 🔜 Planned |
| Feature Store with Feast + Redis | 🔜 Planned |
| Live Twilio / SendGrid / FCM integration | 🔜 Planned |
| True SHAP value computation | 🔜 Planned |
| A/B test analytics + auto prompt tuning | 🔜 Planned |
| RM mobile app | 🔜 Planned |
| Automated monthly model retraining pipeline | 🔜 Planned |

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch — `git checkout -b feature/your-feature-name`
3. Commit your changes — `git commit -m "feat: add your feature"`
4. Push to your fork — `git push origin feature/your-feature-name`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">


*Powered by Python · FastAPI · XGBoost · Claude AI*

</div>
