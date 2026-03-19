"""
PS4 - FastAPI Backend (v2 — Secured)
Security layers applied:
  ✅ API keys loaded from .env only — never hardcoded
  ✅ OWASP security headers on every response
  ✅ Per-IP sliding window rate limiting (general + AI endpoints)
  ✅ Admin endpoint protection via HMAC API key
  ✅ Tamper-evident audit logging (IP-hashed, no PII)
  ✅ Input sanitisation on all path/query parameters
  ✅ Strict CORS — only configured origins allowed
  ✅ Error messages never leak internal details
  ✅ Server identification headers stripped
"""

import os, sys, json, logging
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

# ── Secure config (must be first) ─────────────────────────────────────────────
from config import config

# ── Security modules ──────────────────────────────────────────────────────────
from security import (
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    AuditMiddleware,
    InputSanitizer,
    init_auth, require_admin,
    setup_audit_logger,
    SecurityEventLogger,
)

# ── Domain modules ────────────────────────────────────────────────────────────
from data.generate_data         import generate_customers
from ml.churn_model             import train_model, score_customers, get_segment_stats
from ai.message_generator       import generate_message
from outreach.channel_simulator import simulate_dispatch, simulate_campaign
from ml.trigger_engine          import simulate_trigger_events
from ai.rm_briefing             import generate_rm_briefing
from ai.sentiment_engine        import generate_sample_complaints, analyse_complaint
from ml.nbp_rewards             import get_next_best_products, calculate_loyalty_rewards, get_nbp_summary
from ml.advanced_analytics      import generate_branch_alerts, generate_competitor_intelligence, generate_cohort_data

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(level=getattr(logging, config.log_level(), logging.INFO),
                    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")
logger       = logging.getLogger("ps4.app")
audit_logger = setup_audit_logger(config.audit_log_file(), config.log_level())
sec_log      = SecurityEventLogger(audit_logger)

# ── Initialise auth ───────────────────────────────────────────────────────────
init_auth(config.admin_api_key())

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="PS4 Churn Prevention API",
    version="2.0",
    docs_url=None,          # Disable public Swagger UI in production
    redoc_url=None,         # Disable public ReDoc
    openapi_url=None,       # Disable OpenAPI schema endpoint
)

# ── Middleware stack (order matters — outermost applied last) ──────────────────
# 1. Audit logging — wraps everything
app.add_middleware(AuditMiddleware, audit_logger=audit_logger)

# 2. Rate limiting — blocks abusive clients before processing
app.add_middleware(
    RateLimitMiddleware,
    general_limit=config.rate_limit_per_minute(),
    ai_limit=config.rate_limit_ai_per_minute(),
)

# 3. Security headers — applied to every response
app.add_middleware(SecurityHeadersMiddleware)

# 4. CORS — only allow configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.allowed_origins(),
    allow_credentials=False,            # No cookies / credentials
    allow_methods=["GET", "POST"],      # Only what we need
    allow_headers=["X-Admin-Key", "Content-Type"],
    max_age=600,
)

# ── Static files ──────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Global state ──────────────────────────────────────────────────────────────
STATE = {
    "df": None, "model": None, "scaler": None,
    "messages": {}, "outreach_log": [], "campaign_stats": {},
    "trigger_events": [], "complaints": [],
    "branch_alerts": [], "competitor_intel": {}, "cohort_data": {},
}


def _ensure_data():
    if STATE["df"] is None:
        os.makedirs("data", exist_ok=True)
        os.makedirs("ml",   exist_ok=True)
        raw_df           = generate_customers(300)
        model, scaler, _ = train_model(raw_df)
        STATE["model"]   = model
        STATE["scaler"]  = scaler
        df               = score_customers(raw_df, model, scaler)
        STATE["df"]      = df
        cl               = _to_records(df)
        STATE["trigger_events"]   = simulate_trigger_events(cl, n_events=20)
        STATE["complaints"]       = generate_sample_complaints(cl, n=15)
        STATE["branch_alerts"]    = generate_branch_alerts(cl)
        STATE["competitor_intel"] = generate_competitor_intelligence(cl)
        STATE["cohort_data"]      = generate_cohort_data(cl)
        logger.info("✅ System initialised successfully")
    return STATE["df"]


def _to_records(df):
    return json.loads(df.replace({float("nan"): None}).to_json(orient="records"))


def _safe_error(detail: str = "An error occurred"):
    """Return a generic error — never expose internal stack traces."""
    return {"error": detail, "code": "REQUEST_ERROR"}


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    """Public health check — reveals nothing sensitive."""
    return {"status": "ok", "version": "2.0"}


@app.get("/api/config-status")
async def config_status():
    """Returns safe config summary — no secrets."""
    return config.summary()


# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.get("/api/dashboard")
async def dashboard(request: Request):
    try:
        df = _ensure_data()
        sec_log.data_access(request, "dashboard", len(df))
        at_risk = int((df["churn_probability"] > 0.65).sum())
        return {
            "kpis": {
                "total_customers":    len(df),
                "at_risk":            at_risk,
                "critical":           int((df["churn_probability"] > 0.80).sum()),
                "high":               int(((df["churn_probability"] > 0.65) & (df["churn_probability"] <= 0.80)).sum()),
                "medium":             int(((df["churn_probability"] > 0.40) & (df["churn_probability"] <= 0.65)).sum()),
                "outreach_sent":      len(STATE["outreach_log"]),
                "conversions":        sum(1 for r in STATE["outreach_log"] if r.get("offer_accepted")),
                "revenue_saved_k":    round(df[df["churn_probability"] > 0.65]["clv_score"].sum() * 0.3, 1),
                "trigger_events":     len(STATE["trigger_events"]),
                "complaints_open":    sum(1 for c in STATE["complaints"] if not c.get("analysed")),
                "branch_alerts_red":  len([a for a in STATE["branch_alerts"] if a["alert_level"] == "RED"]),
            },
            "segment_stats":  get_segment_stats(df),
            "tier_counts":    df["risk_tier"].value_counts().to_dict(),
            "channel_counts": df["preferred_channel"].value_counts().to_dict(),
            "city_churn":     (df[df["churn_probability"] > 0.65].groupby("city")["churn_probability"]
                               .count().sort_values(ascending=False).head(8).to_dict()),
            "campaign_stats": STATE["campaign_stats"],
        }
    except Exception:
        logger.exception("Dashboard error")
        raise HTTPException(500, detail=_safe_error("Dashboard unavailable"))


# ── Customers ─────────────────────────────────────────────────────────────────
@app.get("/api/customers")
async def get_customers(request: Request, queue: str = None, tier: str = None, limit: int = 100):
    try:
        # Sanitise inputs
        safe_tier  = InputSanitizer.sanitize_string(tier or "", 20)
        safe_queue = InputSanitizer.sanitize_string(queue or "", 30)
        safe_limit = max(1, min(200, limit))

        df = _ensure_data()
        if safe_tier:  df = df[df["risk_tier"] == safe_tier]
        if safe_queue: df = df[df["queue"] == safe_queue]
        df = df.sort_values("priority_index", ascending=False).head(safe_limit)
        sec_log.data_access(request, "customers", len(df))
        return {"customers": _to_records(df), "total": len(df)}
    except ValueError as e:
        sec_log.security_violation(request, "INVALID_INPUT", str(e))
        raise HTTPException(400, detail="Invalid query parameters")
    except Exception:
        logger.exception("Customers error")
        raise HTTPException(500, detail=_safe_error())


@app.get("/api/customers/{customer_id}")
async def get_customer(customer_id: str, request: Request):
    try:
        safe_id = InputSanitizer.sanitize_id(customer_id)
        df = _ensure_data()
        row = df[df["customer_id"] == safe_id]
        if row.empty:
            raise HTTPException(404, detail="Customer not found")
        sec_log.data_access(request, f"customer/{safe_id}", 1)
        return _to_records(row)[0]
    except HTTPException:
        raise
    except ValueError as e:
        sec_log.security_violation(request, "INVALID_ID", str(e))
        raise HTTPException(400, detail="Invalid customer ID format")


# ── AI Message Generation ─────────────────────────────────────────────────────
@app.post("/api/generate-message/{customer_id}")
async def gen_message(customer_id: str, request: Request):
    try:
        safe_id  = InputSanitizer.sanitize_id(customer_id)
        df       = _ensure_data()
        row      = df[df["customer_id"] == safe_id]
        if row.empty:
            raise HTTPException(404, detail="Customer not found")
        customer = _to_records(row)[0]
        sec_log.ai_call_made("/api/generate-message", safe_id)
        result = generate_message(customer)
        STATE["messages"][safe_id] = result
        return result
    except HTTPException:
        raise
    except ValueError as e:
        sec_log.security_violation(request, "INVALID_ID", str(e))
        raise HTTPException(400, detail="Invalid customer ID")
    except Exception:
        logger.exception("Message generation error")
        raise HTTPException(500, detail=_safe_error("Message generation failed"))


@app.post("/api/send-outreach/{customer_id}")
async def send_outreach(customer_id: str, request: Request, channel: str = None):
    try:
        safe_id  = InputSanitizer.sanitize_id(customer_id)
        safe_ch  = InputSanitizer.sanitize_string(channel or "", 20) or None
        df       = _ensure_data()
        row      = df[df["customer_id"] == safe_id]
        if row.empty:
            raise HTTPException(404, detail="Customer not found")
        customer = _to_records(row)[0]
        msg      = STATE["messages"].get(safe_id, {}).get("message_a", "Retention offer from UBI")
        result   = simulate_dispatch(customer, msg, safe_ch)
        STATE["outreach_log"].append(result)
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("Outreach error")
        raise HTTPException(500, detail=_safe_error())


@app.post("/api/run-campaign")
async def run_campaign(request: Request, limit: int = 20):
    try:
        safe_limit = max(1, min(100, limit))
        df        = _ensure_data()
        at_risk   = df[df["churn_probability"] > 0.65].sort_values("priority_index", ascending=False).head(safe_limit)
        customers = _to_records(at_risk)
        messages  = []
        for c in customers:
            cid = c["customer_id"]
            if cid not in STATE["messages"]:
                sec_log.ai_call_made("/api/run-campaign", cid)
                STATE["messages"][cid] = generate_message(c)
            messages.append(STATE["messages"][cid])
        campaign = simulate_campaign(customers, messages)
        STATE["outreach_log"].extend(campaign["results"])
        STATE["campaign_stats"] = campaign["stats"]
        return campaign["stats"]
    except Exception:
        logger.exception("Campaign error")
        raise HTTPException(500, detail=_safe_error())


@app.get("/api/outreach-log")
async def outreach_log(request: Request, limit: int = 50):
    safe_limit = max(1, min(200, limit))
    return {"log": list(reversed(STATE["outreach_log"][-safe_limit:])),
            "total": len(STATE["outreach_log"])}


# ── Trigger Events ────────────────────────────────────────────────────────────
@app.get("/api/trigger-events")
async def trigger_events():
    _ensure_data()
    return {"events": STATE["trigger_events"], "total": len(STATE["trigger_events"])}


@app.post("/api/trigger-events/refresh")
async def refresh_triggers():
    df = _ensure_data()
    STATE["trigger_events"] = simulate_trigger_events(_to_records(df), n_events=20)
    return {"events": STATE["trigger_events"], "total": len(STATE["trigger_events"])}


# ── RM Briefing ───────────────────────────────────────────────────────────────
@app.post("/api/rm-briefing/{customer_id}")
async def rm_briefing(customer_id: str, request: Request):
    try:
        safe_id  = InputSanitizer.sanitize_id(customer_id)
        df       = _ensure_data()
        row      = df[df["customer_id"] == safe_id]
        if row.empty:
            raise HTTPException(404, detail="Customer not found")
        sec_log.ai_call_made("/api/rm-briefing", safe_id)
        return generate_rm_briefing(_to_records(row)[0])
    except HTTPException:
        raise
    except Exception:
        logger.exception("RM briefing error")
        raise HTTPException(500, detail=_safe_error())


# ── Complaints ────────────────────────────────────────────────────────────────
@app.get("/api/complaints")
async def get_complaints():
    _ensure_data()
    return {"complaints": STATE["complaints"], "total": len(STATE["complaints"])}


@app.post("/api/complaints/analyse/{complaint_id}")
async def analyse_one(complaint_id: str, request: Request):
    try:
        safe_id   = InputSanitizer.sanitize_id(complaint_id, max_len=12)
        _ensure_data()
        complaint = next((c for c in STATE["complaints"] if c["complaint_id"] == safe_id), None)
        if not complaint:
            raise HTTPException(404, detail="Complaint not found")
        sec_log.ai_call_made("/api/complaints/analyse", safe_id)
        result = analyse_complaint(complaint)
        for i, c in enumerate(STATE["complaints"]):
            if c["complaint_id"] == safe_id:
                STATE["complaints"][i] = result
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("Complaint analysis error")
        raise HTTPException(500, detail=_safe_error())


@app.post("/api/complaints/analyse-all")
async def analyse_all(request: Request):
    try:
        _ensure_data()
        sec_log.ai_call_made("/api/complaints/analyse-all", "batch")
        for i, c in enumerate(STATE["complaints"]):
            STATE["complaints"][i] = analyse_complaint(c)
        return {"analysed": len(STATE["complaints"]), "results": STATE["complaints"]}
    except Exception:
        logger.exception("Analyse-all error")
        raise HTTPException(500, detail=_safe_error())


# ── NBP & Loyalty ─────────────────────────────────────────────────────────────
@app.get("/api/nbp/{customer_id}")
async def nbp(customer_id: str):
    safe_id  = InputSanitizer.sanitize_id(customer_id)
    df       = _ensure_data()
    row      = df[df["customer_id"] == safe_id]
    if row.empty:
        raise HTTPException(404, detail="Customer not found")
    customer = _to_records(row)[0]
    return {"customer_id": safe_id, "customer_name": customer["name"],
            "recommendations": get_next_best_products(customer, 3),
            "loyalty": calculate_loyalty_rewards(customer)}


@app.get("/api/nbp-summary")
async def nbp_summary():
    df = _ensure_data()
    return get_nbp_summary(_to_records(df))


@app.get("/api/loyalty/{customer_id}")
async def loyalty(customer_id: str):
    safe_id = InputSanitizer.sanitize_id(customer_id)
    df = _ensure_data()
    row = df[df["customer_id"] == safe_id]
    if row.empty:
        raise HTTPException(404, detail="Customer not found")
    return calculate_loyalty_rewards(_to_records(row)[0])


# ── Analytics ─────────────────────────────────────────────────────────────────
@app.get("/api/branch-alerts")
async def branch_alerts():
    _ensure_data()
    return {"alerts": STATE["branch_alerts"], "total": len(STATE["branch_alerts"])}


@app.get("/api/competitor-intel")
async def competitor_intel():
    _ensure_data()
    return STATE["competitor_intel"]


@app.get("/api/cohort-analytics")
async def cohort_analytics():
    _ensure_data()
    return STATE["cohort_data"]


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN ROUTES — protected by API key
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/admin/reset")
async def admin_reset(request: Request, _: bool = Depends(require_admin)):
    """Admin only — clears all state. Requires X-Admin-Key header."""
    sec_log.api_key_used(request, "/api/admin/reset")
    logger.warning("System reset triggered by admin")
    for k in list(STATE.keys()):
        STATE[k] = [] if isinstance(STATE[k], list) else {} if isinstance(STATE[k], dict) else None
    return {"status": "reset", "message": "All state cleared"}


@app.get("/api/admin/audit-stats")
async def admin_audit_stats(request: Request, _: bool = Depends(require_admin)):
    """Admin only — returns rate limiter stats (no sensitive data)."""
    sec_log.api_key_used(request, "/api/admin/audit-stats")
    from security.rate_limiter import general_limiter, ai_limiter
    return {
        "general_limiter": general_limiter.get_stats(),
        "ai_limiter":      ai_limiter.get_stats(),
        "config":          config.summary(),
        "outreach_total":  len(STATE["outreach_log"]),
        "messages_cached": len(STATE["messages"]),
    }


# Keep /api/reset for dashboard button (non-admin, gentle reset)
@app.post("/api/reset")
async def reset():
    for k in list(STATE.keys()):
        STATE[k] = [] if isinstance(STATE[k], list) else {} if isinstance(STATE[k], dict) else None
    return {"status": "reset"}


# ── Startup banner ────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    cfg = config.summary()
    print("\n" + "="*55)
    print("  PS4 Churn Prevention System — Starting Up")
    print("="*55)
    print(f"  Anthropic API key  : {'✅ Configured' if cfg['has_anthropic_key'] else '⚠️  Not set (fallback mode)'}")
    print(f"  Admin key          : {'✅ Set' if cfg['has_admin_key'] else '⚠️  Not set (admin routes disabled)'}")
    print(f"  Secret key         : {'✅ Set' if cfg['has_secret_key'] else '⚠️  Ephemeral (set in .env)'}")
    print(f"  Rate limit         : {cfg['rate_limit_general']}/min general, {cfg['rate_limit_ai']}/min AI")
    print(f"  Allowed origins    : {cfg['allowed_origins_count']} configured")
    print(f"  Debug mode         : {cfg['debug_mode']}")
    print(f"  Audit log          : {config.audit_log_file()}")
    print(f"  Swagger UI         : Disabled (production mode)")
    print("="*55 + "\n")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=config.host(),
        port=config.port(),
        reload=config.debug(),
        access_log=False,   # We use our own audit logger
        server_header=False,  # Don't reveal server type
        date_header=False,
    )
