"""
PS4 - Channel Outreach Simulator
Simulates multi-channel message dispatch with realistic outcomes
"""

import random, time
from datetime import datetime, timedelta

CHANNEL_CONFIG = {
    "WhatsApp": {"open_rate": 0.85, "click_rate": 0.42, "response_rate": 0.28, "icon": "💬"},
    "Push":     {"open_rate": 0.62, "click_rate": 0.30, "response_rate": 0.18, "icon": "🔔"},
    "SMS":      {"open_rate": 0.78, "click_rate": 0.22, "response_rate": 0.12, "icon": "📱"},
    "Email":    {"open_rate": 0.38, "click_rate": 0.15, "response_rate": 0.08, "icon": "📧"},
    "RM Call":  {"open_rate": 0.70, "click_rate": 0.55, "response_rate": 0.45, "icon": "📞"},
}

CHANNEL_PRIORITY = ["WhatsApp", "Push", "SMS", "Email", "RM Call"]

DND_RATE = 0.05   # 5% of customers on DND


def select_channel(customer: dict) -> str:
    """Select best channel based on customer preference and priority."""
    preferred = customer.get("preferred_channel", "WhatsApp")
    if preferred in CHANNEL_PRIORITY:
        return preferred
    return "WhatsApp"


def simulate_dispatch(customer: dict, message: str, channel: str = None) -> dict:
    """Simulate sending a message and track response."""
    if channel is None:
        channel = select_channel(customer)

    # DND check
    if random.random() < DND_RATE:
        return {
            "customer_id": customer["customer_id"],
            "channel":     channel,
            "status":      "BLOCKED",
            "reason":      "Customer on DND registry",
            "timestamp":   datetime.now().isoformat(),
        }

    cfg = CHANNEL_CONFIG[channel]

    # Simulate delivery
    delivered  = random.random() < 0.97
    opened     = delivered and (random.random() < cfg["open_rate"])
    clicked    = opened    and (random.random() < cfg["click_rate"])
    responded  = clicked   and (random.random() < cfg["response_rate"])
    accepted   = responded and (random.random() < 0.55)

    # Escalation logic
    escalate_to = None
    if not opened:
        idx = CHANNEL_PRIORITY.index(channel)
        if idx + 1 < len(CHANNEL_PRIORITY):
            escalate_to = CHANNEL_PRIORITY[idx + 1]

    send_time = _optimal_send_time(customer)

    result = {
        "customer_id":   customer["customer_id"],
        "name":          customer["name"],
        "channel":       channel,
        "channel_icon":  CHANNEL_CONFIG[channel]["icon"],
        "status":        "SENT" if delivered else "FAILED",
        "delivered":     delivered,
        "opened":        opened,
        "clicked":       clicked,
        "responded":     responded,
        "offer_accepted": accepted,
        "send_time":     send_time,
        "timestamp":     datetime.now().isoformat(),
        "escalate_to":   escalate_to,
        "message_preview": message[:80] + "..." if len(message) > 80 else message,
    }

    if accepted:
        result["updated_churn_score"] = 0.10
        result["action_triggered"]    = "CRM flagged | Churn score reset to 0.10"

    return result


def simulate_campaign(customers: list, messages: list) -> dict:
    """Run a full campaign simulation across multiple customers."""
    results = []
    stats   = {
        "total_sent": 0, "delivered": 0, "opened": 0,
        "clicked": 0, "responded": 0, "accepted": 0,
        "channel_breakdown": {}
    }

    for customer, msg_data in zip(customers, messages):
        channel = select_channel(customer)
        message = msg_data.get("message_a", "")
        result  = simulate_dispatch(customer, message, channel)
        results.append(result)

        if result["status"] == "SENT":
            stats["total_sent"]  += 1
            stats["delivered"]   += int(result["delivered"])
            stats["opened"]      += int(result["opened"])
            stats["clicked"]     += int(result["clicked"])
            stats["responded"]   += int(result["responded"])
            stats["accepted"]    += int(result["offer_accepted"])

            ch = result["channel"]
            stats["channel_breakdown"][ch] = stats["channel_breakdown"].get(ch, 0) + 1

    if stats["total_sent"] > 0:
        stats["open_rate"]       = round(stats["opened"]   / stats["total_sent"] * 100, 1)
        stats["click_rate"]      = round(stats["clicked"]  / stats["total_sent"] * 100, 1)
        stats["conversion_rate"] = round(stats["accepted"] / stats["total_sent"] * 100, 1)

    return {"results": results, "stats": stats}


def _optimal_send_time(customer: dict) -> str:
    """Predict optimal send time (simplified rule-based)."""
    age = customer.get("age", 35)
    if age < 30:    hour = random.choice([19, 20, 21, 22])
    elif age < 50:  hour = random.choice([8, 9, 12, 13, 18, 19])
    else:           hour = random.choice([9, 10, 11, 16, 17])
    tomorrow = datetime.now() + timedelta(days=1)
    return tomorrow.replace(hour=hour, minute=0, second=0).strftime("%Y-%m-%d %H:%M")
