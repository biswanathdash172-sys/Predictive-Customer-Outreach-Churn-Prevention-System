"""
PS4 - FastAPI Backend
Predictive Customer Outreach & Churn Prevention System
Union Bank of India | iDEA Hackathon 2.0 | 2026
"""

import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np

# Internal modules
from data.generate_data  import generate_customers
from ml.churn_model      import train_model, score_customers, get_segment_stats
from ai.message_generator import generate_message
from outreach.channel_simulator import simulate_dispatch, simulate_campaign

# ── App init ──────────────────────────────────────────────────────────────────
app = FastAPI(title="PS4 Churn Prevention API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Global state (in-memory for demo) ─────────────────────────────────────────
STATE = {
    "df":             None,   # scored DataFrame
    "model":          None,
    "scaler":         None,
    "messages":       {},     # customer_id → message dict
    "outreach_log":   [],     # dispatch results
    "campaign_stats": {},
}


def _ensure_data():
    if STATE["df"] is None:
        os.makedirs("data", exist_ok=True)
        os.makedirs("ml",   exist_ok=True)
        raw_df         = generate_customers(300)
        model, scaler, _ = train_model(raw_df)
        STATE["model"]   = model
        STATE["scaler"]  = scaler
        STATE["df"]      = score_customers(raw_df, model, scaler)
    return STATE["df"]


def _df_to_records(df: pd.DataFrame) -> list:
    return json.loads(df.replace({float("nan"): None}).to_json(orient="records"))


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/api/dashboard")
async def dashboard_stats():
    df = _ensure_data()
    at_risk   = int((df["churn_probability"] > 0.65).sum())
    critical  = int((df["churn_probability"] > 0.80).sum())
    high      = int(((df["churn_probability"] > 0.65) & (df["churn_probability"] <= 0.80)).sum())
    medium    = int(((df["churn_probability"] > 0.40) & (df["churn_probability"] <= 0.65)).sum())
    rev_saved = round(df[df["churn_probability"] > 0.65]["clv_score"].sum() * 0.3, 1)

    segment_stats  = get_segment_stats(df)
    tier_counts    = df["risk_tier"].value_counts().to_dict()
    channel_counts = df["preferred_channel"].value_counts().to_dict()
    city_churn     = (df[df["churn_probability"] > 0.65]
                      .groupby("city")["churn_probability"]
                      .count().sort_values(ascending=False).head(8).to_dict())

    return {
        "kpis": {
            "total_customers":  len(df),
            "at_risk":          at_risk,
            "critical":         critical,
            "high":             high,
            "medium":           medium,
            "outreach_sent":    len(STATE["outreach_log"]),
            "conversions":      sum(1 for r in STATE["outreach_log"] if r.get("offer_accepted")),
            "revenue_saved_k":  rev_saved,
        },
        "segment_stats":  segment_stats,
        "tier_counts":    tier_counts,
        "channel_counts": channel_counts,
        "city_churn":     city_churn,
        "campaign_stats": STATE["campaign_stats"],
    }


@app.get("/api/customers")
async def get_customers(queue: str = None, tier: str = None, limit: int = 100):
    df = _ensure_data()
    if queue: df = df[df["queue"] == queue]
    if tier:  df = df[df["risk_tier"] == tier]
    df = df.sort_values("priority_index", ascending=False).head(limit)
    return {"customers": _df_to_records(df), "total": len(df)}


@app.get("/api/customers/{customer_id}")
async def get_customer(customer_id: str):
    df  = _ensure_data()
    row = df[df["customer_id"] == customer_id]
    if row.empty:
        raise HTTPException(404, "Customer not found")
    return _df_to_records(row)[0]


@app.post("/api/generate-message/{customer_id}")
async def gen_message(customer_id: str):
    df  = _ensure_data()
    row = df[df["customer_id"] == customer_id]
    if row.empty:
        raise HTTPException(404, "Customer not found")
    customer = _df_to_records(row)[0]
    result   = generate_message(customer)
    STATE["messages"][customer_id] = result
    return result


@app.post("/api/send-outreach/{customer_id}")
async def send_outreach(customer_id: str, channel: str = None):
    df  = _ensure_data()
    row = df[df["customer_id"] == customer_id]
    if row.empty:
        raise HTTPException(404, "Customer not found")
    customer = _df_to_records(row)[0]
    msg_data = STATE["messages"].get(customer_id, {})
    message  = msg_data.get("message_a", "Re-engage offer from Union Bank of India")
    result   = simulate_dispatch(customer, message, channel)
    STATE["outreach_log"].append(result)
    return result


@app.post("/api/run-campaign")
async def run_campaign(limit: int = 20):
    """Run outreach campaign on top N at-risk customers."""
    df       = _ensure_data()
    at_risk  = df[df["churn_probability"] > 0.65].sort_values(
                    "priority_index", ascending=False).head(limit)
    customers = _df_to_records(at_risk)

    # Generate messages for any missing
    messages = []
    for c in customers:
        cid = c["customer_id"]
        if cid not in STATE["messages"]:
            STATE["messages"][cid] = generate_message(c)
        messages.append(STATE["messages"][cid])

    campaign = simulate_campaign(customers, messages)
    STATE["outreach_log"].extend(campaign["results"])
    STATE["campaign_stats"] = campaign["stats"]
    return campaign["stats"]


@app.get("/api/outreach-log")
async def outreach_log(limit: int = 50):
    log = STATE["outreach_log"][-limit:]
    return {"log": list(reversed(log)), "total": len(STATE["outreach_log"])}


@app.post("/api/reset")
async def reset():
    STATE["df"] = STATE["model"] = STATE["scaler"] = None
    STATE["messages"] = {}
    STATE["outreach_log"] = []
    STATE["campaign_stats"] = {}
    return {"status": "reset"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
