"""
PS4 - RM Pre-Call Briefing Generator (Secure)
API key loaded exclusively from environment — never hardcoded.
"""

import os, sys, re, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import config
import anthropic

logger = logging.getLogger("ps4.ai.rm_briefing")

def _get_client():
    key = config.anthropic_api_key()
    return anthropic.Anthropic(api_key=key) if key else None


def generate_rm_briefing(customer: dict) -> dict:
    client = _get_client()
    if not client:
        return _fallback_briefing(customer, "API key not configured")

    prompt = f"""You are a banking RM coach at Union Bank of India.
RM is calling: {customer['name']}, Age: {customer.get('age','N/A')}, City: {customer.get('city','N/A')}
Tenure: {customer.get('tenure_years','N/A')} yrs, Products: {customer.get('products_held','Savings Account')}
Churn Risk: {customer.get('churn_probability',0.7):.0%} ({customer.get('risk_tier','High')}), Horizon: {customer.get('churn_horizon','60 days')}
Reasons: {customer.get('top_reasons','inactivity')}, Segment: {customer.get('segment','Disengaged')}
CLV: {customer.get('clv_score','N/A')}, CSAT: {customer.get('csat_score','N/A')}
Complaints: {customer.get('complaints_6m',0)}, Salary: ₹{customer.get('monthly_salary','N/A')}
Language: {customer.get('preferred_language','English')}

GREETING: <opening line>
SITUATION_SUMMARY: <2 sentences>
TALKING_POINT_1: <point>
TALKING_POINT_2: <point>
TALKING_POINT_3: <point>
OBJECTION_1: <objection>
HANDLE_1: <response>
OBJECTION_2: <objection>
HANDLE_2: <response>
PRIMARY_OFFER: <offer>
FALLBACK_OFFER: <offer>
CALL_DURATION: <minutes>
SUCCESS_SIGNAL: <signal>
RED_FLAG: <signal>"""

    try:
        r = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=800,
                                   messages=[{"role":"user","content":prompt}])
        return _parse(r.content[0].text.strip(), customer)
    except anthropic.AuthenticationError:
        logger.error("Invalid API key for RM briefing")
        return _fallback_briefing(customer, "Invalid API key")
    except Exception as e:
        logger.error(f"RM briefing error: {type(e).__name__}")
        return _fallback_briefing(customer, "API error")


def _parse(text, customer):
    keys = ["GREETING","SITUATION_SUMMARY","TALKING_POINT_1","TALKING_POINT_2","TALKING_POINT_3",
            "OBJECTION_1","HANDLE_1","OBJECTION_2","HANDLE_2",
            "PRIMARY_OFFER","FALLBACK_OFFER","CALL_DURATION","SUCCESS_SIGNAL","RED_FLAG"]
    result = {}
    for k in keys:
        m = re.search(rf"{k}:\s*(.+?)(?=\n[A-Z_]+:|$)", text, re.DOTALL)
        result[k.lower()] = m.group(1).strip() if m else "—"
    result.update({"customer_id": customer["customer_id"], "customer_name": customer["name"],
                   "risk_tier": customer.get("risk_tier","High"), "clv_score": customer.get("clv_score",0),
                   "generated_at": __import__("datetime").datetime.now().strftime("%d %b %Y, %H:%M")})
    return result


def _fallback_briefing(customer, error):
    n = customer['name'].split()[0]
    return {"customer_id": customer["customer_id"], "customer_name": customer["name"],
            "risk_tier": customer.get("risk_tier","High"), "clv_score": customer.get("clv_score",0),
            "greeting": f"Hello {n}, calling from Union Bank of India. How are you today?",
            "situation_summary": f"{n} shows {customer.get('churn_probability',0.7):.0%} churn risk. Reasons: {customer.get('top_reasons','inactivity')}.",
            "talking_point_1": "Ask about recent banking experience",
            "talking_point_2": "Highlight unexplored products",
            "talking_point_3": "Offer personalised retention deal",
            "objection_1": "I'm happy with my current bank",
            "handle_1": "Acknowledge and pivot to UBI's unique benefits",
            "objection_2": "I don't have time right now",
            "handle_2": "Offer to schedule a callback at their convenience",
            "primary_offer": "Special FD rate of 8.5% — exclusive for existing customers",
            "fallback_offer": "Zero annual fee credit card upgrade",
            "call_duration": "5–8 minutes",
            "success_signal": "Customer asks about offer details",
            "red_flag": "Customer asks how to close account",
            "generated_at": __import__("datetime").datetime.now().strftime("%d %b %Y, %H:%M"),
            "error": error}
