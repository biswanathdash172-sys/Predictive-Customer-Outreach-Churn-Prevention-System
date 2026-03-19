"""
PS4 - Gen-AI Personalised Message Generator (Secure)
API key loaded exclusively from environment — never hardcoded.
"""

import re, logging
import anthropic
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import config

logger = logging.getLogger("ps4.ai.messages")

def _get_client():
    key = config.anthropic_api_key()
    if not key:
        return None
    return anthropic.Anthropic(api_key=key)

SEGMENT_ACTIONS = {
    "Price-Sensitive":  "Offer a higher FD interest rate or zero-fee savings account upgrade.",
    "Disengaged":       "Highlight a useful unused feature like UPI Lite or Sweep FD.",
    "Life-Event":       "Offer a pre-approved home loan or personal loan based on recent salary change.",
    "Complaint-Driven": "Acknowledge past issues empathetically and offer dedicated RM support with a fee waiver.",
    "Product Maturity": "Suggest FD renewal or recommend the next suitable product.",
}
CHANNEL_LIMITS = {"WhatsApp": 300, "SMS": 160, "Email": 600, "Push": 100}


def generate_message(customer: dict) -> dict:
    channel    = customer.get("preferred_channel", "WhatsApp")
    language   = customer.get("preferred_language", "English")
    segment    = customer.get("segment", "Disengaged")
    reasons    = customer.get("top_reasons", "general inactivity")
    char_limit = CHANNEL_LIMITS.get(channel, 300)
    action     = SEGMENT_ACTIONS.get(segment, "Re-engage the customer with a personalised offer.")
    client     = _get_client()

    if not client:
        logger.warning("Anthropic API key not configured — using fallback message")
        return _fallback(customer, channel, language)

    prompt = f"""You are a customer retention specialist at Union Bank of India (UBI).
Customer: {customer['name']}, Segment: {segment}, Risk: {customer.get('risk_tier','High')}
Churn Horizon: {customer.get('churn_horizon','60 days')}, Reasons: {reasons}
Products: {customer.get('products_held','Savings Account')}, Language: {language}, Channel: {channel} (max {char_limit} chars)
Action: {action}
Generate TWO variants. Must NOT violate RBI guidelines. Start with customer's first name.
Format:
VARIANT_A: <message>
VARIANT_B: <message>
COMPLIANCE: PASS or FAIL
COMPLIANCE_NOTE: <one line>"""

    try:
        r = _get_client().messages.create(model="claude-sonnet-4-20250514", max_tokens=600,
                                          messages=[{"role":"user","content":prompt}])
        text = r.content[0].text.strip()
        return {"message_a": _ex(text,"VARIANT_A"), "message_b": _ex(text,"VARIANT_B"),
                "compliance_ok": "PASS" in _ex(text,"COMPLIANCE").upper(),
                "compliance_note": _ex(text,"COMPLIANCE_NOTE"),
                "channel": channel, "language": language}
    except anthropic.AuthenticationError:
        logger.error("Invalid Anthropic API key")
        return _fallback(customer, channel, language, "Invalid API key")
    except anthropic.RateLimitError:
        return _fallback(customer, channel, language, "Rate limit hit")
    except Exception as e:
        logger.error(f"Claude API error: {type(e).__name__}")
        return _fallback(customer, channel, language, "API error")


def _ex(text, key):
    m = re.search(rf"{key}:\s*(.+?)(?=\n[A-Z_]+:|$)", text, re.DOTALL)
    return m.group(1).strip() if m else ""

def _fallback(customer, channel, language, error=""):
    first = customer['name'].split()[0]
    return {"message_a": f"Dear {first}, we have an exclusive offer for you. Contact your RM today.",
            "message_b": f"Hi {first}! You're eligible for a special UBI benefit. Reply to know more.",
            "compliance_ok": True, "compliance_note": f"Fallback message ({error})",
            "channel": channel, "language": language}

def batch_generate(customers):
    return [{**generate_message(c), "customer_id": c["customer_id"]} for c in customers]
