"""
PS4 - Gen-AI Personalised Message Generator
Uses Claude API to craft hyper-personalised retention messages
"""

import os, re
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

SEGMENT_ACTIONS = {
    "Price-Sensitive":  "Offer a higher FD interest rate or zero-fee savings account upgrade.",
    "Disengaged":       "Highlight a useful unused feature like UPI Lite or Sweep FD.",
    "Life-Event":       "Offer a pre-approved home loan or personal loan based on recent salary change.",
    "Complaint-Driven": "Acknowledge past issues empathetically and offer dedicated RM support with a fee waiver.",
    "Product Maturity": "Suggest FD renewal or recommend the next suitable product.",
}

CHANNEL_LIMITS = {
    "WhatsApp": 300,
    "SMS":      160,
    "Email":    600,
    "Push":     100,
}


def generate_message(customer: dict) -> dict:
    """
    Generate a personalised retention message for a customer.
    Returns dict with message_a, message_b, compliance_ok, channel
    """
    channel    = customer.get("preferred_channel", "WhatsApp")
    language   = customer.get("preferred_language", "English")
    segment    = customer.get("segment", "Disengaged")
    reasons    = customer.get("top_reasons", "general inactivity")
    char_limit = CHANNEL_LIMITS.get(channel, 300)
    action     = SEGMENT_ACTIONS.get(segment, "Re-engage the customer with a personalised offer.")

    prompt = f"""You are a customer retention specialist at Union Bank of India (UBI).

Customer Profile:
- Name: {customer['name']}
- Segment: {segment}
- Risk Tier: {customer.get('risk_tier', 'High')}
- Predicted Churn Horizon: {customer.get('churn_horizon', '60 days')}
- Top Churn Reasons: {reasons}
- Products Held: {customer.get('products_held', 'Savings Account')}
- Preferred Language: {language}
- Channel: {channel} (max {char_limit} characters)

Recommended Action: {action}

Task:
Generate TWO message variants (Variant A and Variant B) for this customer.
- Both must be warm, personalised, and address the churn reasons
- Must NOT make false promises or violate RBI guidelines
- Must NOT mention competitor banks by name
- Keep each message under {char_limit} characters
- Write in {language} (use English script even for Indian languages)
- Start with the customer's first name

Respond in this exact format:
VARIANT_A: <message here>
VARIANT_B: <message here>
COMPLIANCE: PASS or FAIL
COMPLIANCE_NOTE: <one line note>"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()

        variant_a = _extract(text, "VARIANT_A")
        variant_b = _extract(text, "VARIANT_B")
        compliance = "PASS" in _extract(text, "COMPLIANCE").upper()
        note       = _extract(text, "COMPLIANCE_NOTE")

        return {
            "message_a":      variant_a,
            "message_b":      variant_b,
            "compliance_ok":  compliance,
            "compliance_note": note,
            "channel":        channel,
            "language":       language,
        }

    except Exception as e:
        # Fallback demo message
        first_name = customer['name'].split()[0]
        return {
            "message_a": f"Dear {first_name}, we value your relationship with Union Bank. We have an exclusive offer for you — please contact your Relationship Manager today.",
            "message_b": f"Hi {first_name}! As a valued UBI customer, you're eligible for a special benefit. Reply to know more or visit your nearest branch.",
            "compliance_ok": True,
            "compliance_note": "Fallback message used (API unavailable)",
            "channel": channel,
            "language": language,
            "error": str(e),
        }


def _extract(text: str, key: str) -> str:
    pattern = rf"{key}:\s*(.+?)(?=\n[A-Z_]+:|$)"
    match   = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""


def batch_generate(customers: list) -> list:
    """Generate messages for a list of customer dicts."""
    results = []
    for c in customers:
        msg = generate_message(c)
        msg["customer_id"] = c["customer_id"]
        results.append(msg)
    return results
