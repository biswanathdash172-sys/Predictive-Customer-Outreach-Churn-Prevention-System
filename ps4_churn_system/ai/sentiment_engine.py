"""
PS4 - Sentiment Analysis Engine (Secure)
API key loaded exclusively from environment — never hardcoded.
"""

import os, sys, re, random, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import config
import anthropic

logger = logging.getLogger("ps4.ai.sentiment")

def _get_client():
    key = config.anthropic_api_key()
    return anthropic.Anthropic(api_key=key) if key else None

COMPLAINT_TEMPLATES = [
    "I have been waiting 3 weeks for my credit card issue. Nobody calls back. Very disappointed.",
    "Your ATM swallowed my card 10 days ago and I still haven't got it back. This is ridiculous.",
    "Why is my account balance wrong? I've called 4 times but no one helps. Thinking of moving to HDFC.",
    "The FD interest rate was changed without notice. I want to close my account.",
    "Net banking crashes when I try to pay bills. Very poor service.",
    "I was charged ₹500 fee without prior notice. Refund it immediately.",
    "Customer care put me on hold 45 minutes then disconnected. Worst experience.",
    "Home loan EMI deducted twice this month. Account is negative. Fix this TODAY.",
    "Nobody responds to my emails. 5 emails in 2 weeks. Anyone working there?",
    "Branch staff was rude. 8-year customer — this is how you treat me?",
    "Never got my debit card renewed after 3 requests. Can't do online transactions.",
    "UPI payments failing for 2 weeks. Other banks work fine.",
    "Credit limit reduced without my knowledge. Affecting my CIBIL score.",
    "Loan disbursement promised in 5 days — 3 weeks now. Urgent need of funds.",
    "Moving all savings to another bank if service quality continues.",
]

SENTIMENT_LEVELS = {
    "furious":      {"score": 0.9, "color": "#ff4757", "label": "🔴 Furious"},
    "very_angry":   {"score": 0.75, "color": "#ff6b35", "label": "🟠 Very Angry"},
    "frustrated":   {"score": 0.55, "color": "#ffd166", "label": "🟡 Frustrated"},
    "disappointed": {"score": 0.35, "color": "#74b9ff", "label": "🔵 Disappointed"},
    "neutral":      {"score": 0.15, "color": "#00e5a0", "label": "🟢 Neutral"},
}


def generate_sample_complaints(customers, n=12):
    complaints = []
    for i in range(n):
        c = random.choice(customers)
        complaints.append({
            "complaint_id":   f"CMP{20000+i}",
            "customer_id":    c["customer_id"],
            "customer_name":  c["name"],
            "city":           c.get("city","Unknown"),
            "complaint_text": random.choice(COMPLAINT_TEMPLATES),
            "channel":        random.choice(["Call Centre","Email","Branch","Twitter","App"]),
            "date":           f"{random.randint(1,28):02d} Mar 2026",
            "analysed":       False,
        })
    return complaints


def analyse_complaint(complaint: dict) -> dict:
    client = _get_client()

    if client:
        prompt = f"""Banking customer experience analyst at Union Bank of India.
Customer: {complaint['customer_name']} (ID: {complaint['customer_id']})
Channel: {complaint.get('channel','Unknown')}
Complaint: "{complaint['complaint_text']}"

SENTIMENT: <furious/very_angry/frustrated/disappointed/neutral>
ANGER_SCORE: <0.0-1.0>
CHURN_INTENT: <HIGH/MEDIUM/LOW>
URGENCY: <IMMEDIATE/WITHIN_24H/WITHIN_WEEK>
CORE_ISSUE: <one sentence>
EMOTION_WORDS: <comma-separated>
RESOLUTION_PRIORITY: <1-5>
RECOMMENDED_RESPONSE: <one action>
ESCALATE_TO_RM: <YES/NO>
CHURN_SIGNAL_DETECTED: <YES/NO>"""

        try:
            r = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=400,
                                       messages=[{"role":"user","content":prompt}])
            result = _parse_sentiment(r.content[0].text.strip())
        except anthropic.AuthenticationError:
            logger.error("Invalid API key for sentiment analysis")
            result = _rule_based(complaint["complaint_text"])
        except Exception as e:
            logger.error(f"Sentiment API error: {type(e).__name__}")
            result = _rule_based(complaint["complaint_text"])
    else:
        result = _rule_based(complaint["complaint_text"])

    result.update({k: complaint[k] for k in ["complaint_id","customer_id","customer_name",
                                               "complaint_text","channel","date"]})
    result["analysed"] = True
    cfg = SENTIMENT_LEVELS.get(result.get("sentiment","frustrated"), SENTIMENT_LEVELS["frustrated"])
    result["sentiment_label"] = cfg["label"]
    result["sentiment_color"] = cfg["color"]
    return result


def _parse_sentiment(text):
    fields = ["SENTIMENT","ANGER_SCORE","CHURN_INTENT","URGENCY","CORE_ISSUE",
              "EMOTION_WORDS","RESOLUTION_PRIORITY","RECOMMENDED_RESPONSE",
              "ESCALATE_TO_RM","CHURN_SIGNAL_DETECTED"]
    result = {}
    for f in fields:
        m = re.search(rf"{f}:\s*(.+?)(?=\n[A-Z_]+:|$)", text, re.DOTALL)
        result[f.lower()] = m.group(1).strip() if m else "—"
    try: result["anger_score"] = float(result["anger_score"])
    except: result["anger_score"] = 0.5
    return result


def _rule_based(text):
    t = text.lower()
    score = 0.3
    if any(w in t for w in ["close","leaving","hdfc","icici","moving"]): score += 0.3
    if any(w in t for w in ["ridiculous","cheating","worst","unacceptable"]): score += 0.25
    if any(w in t for w in ["waiting","no response","nobody","still"]): score += 0.15
    score = min(0.99, score)
    if score > 0.75:   senti = "furious"
    elif score > 0.6:  senti = "very_angry"
    elif score > 0.4:  senti = "frustrated"
    elif score > 0.2:  senti = "disappointed"
    else:              senti = "neutral"
    churn = any(w in t for w in ["close","leaving","hdfc","icici","sbi","axis","another bank"])
    return {"sentiment": senti, "anger_score": round(score,2),
            "churn_intent": "HIGH" if score>0.65 else "MEDIUM" if score>0.4 else "LOW",
            "urgency": "IMMEDIATE" if score>0.75 else "WITHIN_24H" if score>0.5 else "WITHIN_WEEK",
            "core_issue": "Service failure and poor resolution time",
            "emotion_words": "disappointed, frustrated, urgent",
            "resolution_priority": str(min(5,int(score*5)+1)),
            "recommended_response": "Assign senior RM and call back within 2 hours",
            "escalate_to_rm": "YES" if score>0.6 else "NO",
            "churn_signal_detected": "YES" if churn else "NO"}
