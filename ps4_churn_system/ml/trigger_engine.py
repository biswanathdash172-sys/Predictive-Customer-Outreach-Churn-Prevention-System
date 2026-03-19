"""
PS4 - Real-Time Trigger Event Scoring Engine
Detects high-risk customer behaviour in real-time and fires immediate alerts
"""

import random
from datetime import datetime, timedelta

# Trigger event types with risk weight and description
TRIGGER_EVENTS = {
    "LARGE_OUTFLOW":      {"weight": 0.35, "label": "Large fund transfer out",        "icon": "💸", "severity": "critical"},
    "UPI_MANDATE_NEW":    {"weight": 0.28, "label": "New UPI mandate to competitor",  "icon": "🔗", "severity": "critical"},
    "APP_UNINSTALL":      {"weight": 0.30, "label": "Mobile app uninstalled",         "icon": "📵", "severity": "critical"},
    "COMPLAINT_FILED":    {"weight": 0.22, "label": "New complaint filed",            "icon": "😠", "severity": "high"},
    "FD_PREMATURE":       {"weight": 0.25, "label": "FD broken prematurely",          "icon": "🏦", "severity": "high"},
    "LOGIN_DROP":         {"weight": 0.15, "label": "Login frequency dropped >60%",   "icon": "📉", "severity": "medium"},
    "CREDIT_MAXED":       {"weight": 0.18, "label": "Credit card maxed out",          "icon": "💳", "severity": "medium"},
    "SALARY_REROUTED":    {"weight": 0.32, "label": "Salary credited to other bank",  "icon": "💰", "severity": "critical"},
    "BRANCH_VISIT_CLOSE": {"weight": 0.12, "label": "Asked for account closure form", "icon": "🚪", "severity": "critical"},
    "EMI_MISSED":         {"weight": 0.20, "label": "EMI payment missed",             "icon": "⏰", "severity": "high"},
}


def simulate_trigger_events(customers: list, n_events: int = 15) -> list:
    """Simulate real-time trigger events arriving from the CBS / event stream."""
    events = []
    severities = ["critical", "critical", "high", "high", "medium"]

    for i in range(n_events):
        customer   = random.choice(customers)
        event_key  = random.choice(list(TRIGGER_EVENTS.keys()))
        event_cfg  = TRIGGER_EVENTS[event_key]
        base_score = customer.get("churn_probability", 0.5)

        # Bump score by event weight, cap at 0.99
        new_score = min(0.99, base_score + event_cfg["weight"] + random.uniform(-0.05, 0.05))

        events.append({
            "event_id":       f"EVT{10000 + i}",
            "customer_id":    customer["customer_id"],
            "customer_name":  customer["name"],
            "city":           customer.get("city", "Unknown"),
            "event_type":     event_key,
            "event_label":    event_cfg["label"],
            "event_icon":     event_cfg["icon"],
            "severity":       event_cfg["severity"],
            "old_score":      round(base_score, 3),
            "new_score":      round(new_score, 3),
            "score_delta":    round(new_score - base_score, 3),
            "timestamp":      (datetime.now() - timedelta(minutes=random.randint(0, 120))).strftime("%H:%M:%S"),
            "recommended_action": _get_action(event_key),
            "auto_queued":    new_score > 0.65,
        })

    events.sort(key=lambda x: x["new_score"], reverse=True)
    return events


def _get_action(event_type: str) -> str:
    actions = {
        "LARGE_OUTFLOW":      "Call RM immediately — offer FD rate upgrade",
        "UPI_MANDATE_NEW":    "Send WhatsApp with zero-fee account offer",
        "APP_UNINSTALL":      "Send Push + SMS with re-engagement offer",
        "COMPLAINT_FILED":    "Escalate to senior RM + issue service credit",
        "FD_PREMATURE":       "Offer special renewal rate via WhatsApp",
        "LOGIN_DROP":         "Send app re-engagement push notification",
        "CREDIT_MAXED":       "Offer credit limit increase via Email",
        "SALARY_REROUTED":    "Immediate RM call — offer salary account benefits",
        "BRANCH_VISIT_CLOSE": "Senior RM intervention + retention offer package",
        "EMI_MISSED":         "Offer EMI moratorium or restructuring via call",
    }
    return actions.get(event_type, "Review customer profile and contact via preferred channel")
