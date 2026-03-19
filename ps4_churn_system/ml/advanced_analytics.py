"""
PS4 - Advanced Analytics Module
Branch-level alerts, competitor intelligence, cohort retention curves
"""

import random
from datetime import datetime, timedelta
from collections import defaultdict

COMPETITORS = ["HDFC Bank", "ICICI Bank", "SBI", "Axis Bank", "Kotak Bank", "IDFC First"]

# ── Branch Alerts ──────────────────────────────────────────────────────────────

def generate_branch_alerts(scored_customers: list) -> list:
    """
    Generate morning branch alerts — at-risk customers likely to visit today.
    In production: cross-reference branch visit history + appointment calendar.
    """
    alerts = []
    cities = list({c.get("city","Unknown") for c in scored_customers})

    for city in cities:
        city_customers = [c for c in scored_customers if c.get("city") == city]
        at_risk        = [c for c in city_customers if c.get("churn_probability", 0) > 0.55]
        critical       = [c for c in at_risk if c.get("churn_probability", 0) > 0.80]
        revenue_at_risk = round(sum(c.get("clv_score", 0) for c in at_risk) * 0.4, 1)

        if not at_risk:
            continue

        # Pick 1–3 customers likely to visit today
        likely_visitors = random.sample(at_risk, min(3, len(at_risk)))

        alerts.append({
            "city":              city,
            "branch_code":       f"UBI{city[:3].upper()}{random.randint(100,999)}",
            "total_customers":   len(city_customers),
            "at_risk_count":     len(at_risk),
            "critical_count":    len(critical),
            "revenue_at_risk_k": revenue_at_risk,
            "risk_pct":          round(len(at_risk) / max(len(city_customers), 1) * 100, 1),
            "alert_level":       "RED" if len(critical) >= 3 else "AMBER" if len(at_risk) >= 5 else "GREEN",
            "likely_visitors":   [{"name": c["name"], "risk": f"{c.get('churn_probability',0):.0%}",
                                   "segment": c.get("segment",""), "id": c["customer_id"]}
                                  for c in likely_visitors],
            "top_rm_action":     _branch_action(len(critical), revenue_at_risk),
            "generated_at":      datetime.now().strftime("%d %b %Y, %H:%M"),
        })

    alerts.sort(key=lambda x: x["critical_count"], reverse=True)
    return alerts


def _branch_action(critical: int, revenue: float) -> str:
    if critical >= 5 or revenue > 500:
        return "🚨 Activate full branch retention protocol — alert senior RM and branch manager"
    elif critical >= 2:
        return "⚠️ Assign dedicated RM to all critical-tier customers visiting today"
    else:
        return "📋 Brief front desk staff on at-risk customers — flag for warm handoff to RM"


# ── Competitor Intelligence ───────────────────────────────────────────────────

def generate_competitor_intelligence(scored_customers: list) -> dict:
    """
    Analyse cross-bank outflow patterns to identify which competitor
    is stealing the most customers and from which cities.
    """
    outflow_customers = [c for c in scored_customers if c.get("cross_bank_outflow") == 1]

    # Simulate which competitor they're moving to
    competitor_map = {}
    city_competitor = defaultdict(lambda: defaultdict(int))

    for c in outflow_customers:
        competitor = random.choices(
            COMPETITORS,
            weights=[30, 25, 20, 12, 8, 5],  # HDFC most common
            k=1
        )[0]
        competitor_map[c["customer_id"]] = competitor
        city_competitor[c.get("city","Unknown")][competitor] += 1

    # Aggregate by competitor
    competitor_counts = defaultdict(int)
    competitor_clv    = defaultdict(float)
    for cid, comp in competitor_map.items():
        competitor_counts[comp] += 1
        cust = next((c for c in scored_customers if c["customer_id"] == cid), {})
        competitor_clv[comp] += cust.get("clv_score", 0)

    competitor_stats = [
        {
            "competitor":    comp,
            "customers_lost": competitor_counts[comp],
            "clv_at_risk":   round(competitor_clv[comp], 1),
            "pct_of_outflow": round(competitor_counts[comp] / max(len(outflow_customers), 1) * 100, 1),
        }
        for comp in COMPETITORS if comp in competitor_counts
    ]
    competitor_stats.sort(key=lambda x: x["customers_lost"], reverse=True)

    # Top cities losing customers
    city_leakage = [
        {
            "city":          city,
            "outflow_count": sum(comps.values()),
            "top_competitor": max(comps, key=comps.get),
        }
        for city, comps in city_competitor.items()
    ]
    city_leakage.sort(key=lambda x: x["outflow_count"], reverse=True)

    return {
        "total_outflow_customers": len(outflow_customers),
        "estimated_clv_loss":      round(sum(competitor_clv.values()), 1),
        "competitor_stats":        competitor_stats,
        "city_leakage":            city_leakage[:8],
        "top_competitor":          competitor_stats[0]["competitor"] if competitor_stats else "HDFC Bank",
        "insight":                 _competitor_insight(competitor_stats),
        "generated_at":            datetime.now().strftime("%d %b %Y, %H:%M"),
    }


def _competitor_insight(stats: list) -> str:
    if not stats:
        return "No significant competitor outflow detected this period."
    top = stats[0]
    return (f"{top['competitor']} is the primary threat, capturing {top['pct_of_outflow']:.0f}% of outflowing customers. "
            f"Recommend targeted counter-offer campaign against {top['competitor']}'s most promoted products.")


# ── Cohort Retention Curves ───────────────────────────────────────────────────

def generate_cohort_data(scored_customers: list) -> dict:
    """
    Generate synthetic cohort retention curves showing how well
    each campaign retained customers at 30 / 60 / 90 days.
    """
    segments   = ["Price-Sensitive", "Disengaged", "Life-Event", "Complaint-Driven", "Product Maturity"]
    channels   = ["WhatsApp", "Push", "SMS", "Email", "RM Call"]

    # Segment retention curves
    segment_cohorts = {}
    for seg in segments:
        base = random.uniform(0.55, 0.75)
        segment_cohorts[seg] = {
            "30d": round(base, 2),
            "60d": round(base * random.uniform(0.80, 0.92), 2),
            "90d": round(base * random.uniform(0.65, 0.82), 2),
            "customer_count": len([c for c in scored_customers if c.get("segment") == seg]),
        }

    # Channel retention curves
    channel_cohorts = {}
    channel_base = {"WhatsApp": 0.72, "RM Call": 0.68, "SMS": 0.55, "Push": 0.50, "Email": 0.42}
    for ch in channels:
        base = channel_base.get(ch, 0.50)
        channel_cohorts[ch] = {
            "30d": round(base + random.uniform(-0.05, 0.05), 2),
            "60d": round(base * random.uniform(0.80, 0.90), 2),
            "90d": round(base * random.uniform(0.65, 0.80), 2),
        }

    # Monthly campaign performance (last 6 months)
    months = ["Oct 2025", "Nov 2025", "Dec 2025", "Jan 2026", "Feb 2026", "Mar 2026"]
    monthly_perf = []
    prev_conv = 0.18
    for month in months:
        conv = round(min(0.45, prev_conv + random.uniform(-0.02, 0.06)), 2)
        monthly_perf.append({
            "month":           month,
            "customers_at_risk": random.randint(40, 80),
            "outreach_sent":   random.randint(35, 75),
            "converted":       random.randint(8, 25),
            "conversion_rate": conv,
            "revenue_saved_k": round(random.uniform(50, 200), 1),
        })
        prev_conv = conv

    return {
        "segment_cohorts": segment_cohorts,
        "channel_cohorts": channel_cohorts,
        "monthly_performance": monthly_perf,
        "best_segment":  max(segment_cohorts, key=lambda s: segment_cohorts[s]["90d"]),
        "best_channel":  max(channel_cohorts,  key=lambda c: channel_cohorts[c]["90d"]),
        "avg_90d_retention": round(
            sum(v["90d"] for v in segment_cohorts.values()) / len(segment_cohorts), 2
        ),
    }
