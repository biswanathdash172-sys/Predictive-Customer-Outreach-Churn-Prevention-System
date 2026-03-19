"""
PS4 - Next Best Product (NBP) Model + Loyalty Rewards Engine
Recommends the most suitable product for each customer and auto-triggers rewards
"""

import random

ALL_PRODUCTS = [
    "Savings Account", "Fixed Deposit", "Recurring Deposit",
    "Credit Card", "Home Loan", "Personal Loan",
    "Demat Account", "Insurance", "Mutual Fund SIP",
    "Gold Loan", "Auto Loan", "UPI Lite", "Sweep FD",
]

PRODUCT_RULES = [
    {
        "condition":  lambda c: c.get("monthly_salary", 0) > 80000 and "Home Loan" not in c.get("products_held",""),
        "product":    "Home Loan",
        "reason":     "High income profile qualifies for pre-approved home loan up to ₹60L",
        "offer":      "Pre-approved Home Loan at 8.4% — no processing fee this month",
        "icon":       "🏠",
        "category":   "Loans",
        "score":      0.92,
    },
    {
        "condition":  lambda c: c.get("num_products", 1) <= 2 and "Fixed Deposit" not in c.get("products_held",""),
        "product":    "Fixed Deposit",
        "reason":     "Low product penetration — FD is ideal first investment product",
        "offer":      "Special FD rate of 8.6% for 366 days — exclusive for savings account holders",
        "icon":       "💰",
        "category":   "Investments",
        "score":      0.88,
    },
    {
        "condition":  lambda c: "Credit Card" not in c.get("products_held","") and c.get("csat_score",3) >= 3,
        "product":    "Credit Card",
        "reason":     "No credit card on file — high cross-sell opportunity",
        "offer":      "Zero annual fee UBI Signature Card with 5X reward points on UPI",
        "icon":       "💳",
        "category":   "Cards",
        "score":      0.85,
    },
    {
        "condition":  lambda c: c.get("monthly_salary", 0) > 30000 and "Mutual Fund SIP" not in c.get("products_held",""),
        "product":    "Mutual Fund SIP",
        "reason":     "Salary profile suitable for SIP — growing wealth management segment",
        "offer":      "Start a SIP from ₹500/month — UBI Mutual Fund with zero exit load for 1 year",
        "icon":       "📈",
        "category":   "Investments",
        "score":      0.80,
    },
    {
        "condition":  lambda c: "Insurance" not in c.get("products_held","") and c.get("age",35) < 50,
        "product":    "Life Insurance",
        "reason":     "No insurance coverage — significant protection gap for age group",
        "offer":      "Term insurance plan — ₹1Cr cover at just ₹799/month",
        "icon":       "🛡️",
        "category":   "Insurance",
        "score":      0.78,
    },
    {
        "condition":  lambda c: "Recurring Deposit" not in c.get("products_held","") and c.get("monthly_salary",0) < 50000,
        "product":    "Recurring Deposit",
        "reason":     "Mid-income profile — RD is the ideal disciplined savings tool",
        "offer":      "Recurring Deposit at 7.8% — start from just ₹500/month",
        "icon":       "🔁",
        "category":   "Savings",
        "score":      0.75,
    },
    {
        "condition":  lambda c: "Demat Account" not in c.get("products_held","") and c.get("monthly_salary",0) > 60000,
        "product":    "Demat Account",
        "reason":     "High income with no equity investment — demat is a natural next step",
        "offer":      "Free Demat Account with zero AMC for first year — direct equity + mutual funds",
        "icon":       "📊",
        "category":   "Investments",
        "score":      0.72,
    },
]

REWARD_TRIGGERS = {
    "LOYALTY_5Y":        {"points": 5000,  "label": "5-Year Loyalty Bonus",         "condition": lambda c: c.get("tenure_years",0) >= 5},
    "MULTI_PRODUCT":     {"points": 2000,  "label": "Multi-Product Holder Bonus",   "condition": lambda c: c.get("num_products",0) >= 4},
    "HIGH_TXN":          {"points": 1500,  "label": "Active Transactor Reward",     "condition": lambda c: c.get("txn_freq_monthly",0) >= 20},
    "SALARY_ACCOUNT":    {"points": 3000,  "label": "Salary Account Premium",       "condition": lambda c: c.get("monthly_salary",0) >= 75000},
    "DIGITAL_CHAMPION":  {"points": 1000,  "label": "Digital Banking Champion",     "condition": lambda c: c.get("app_logins_monthly",0) >= 15},
    "RETENTION_SPECIAL": {"points": 8000,  "label": "Special Retention Reward",     "condition": lambda c: c.get("churn_probability",0) > 0.65},
}


def get_next_best_products(customer: dict, top_n: int = 3) -> list:
    """Return top N product recommendations for a customer."""
    recommendations = []
    held = customer.get("products_held", "")

    for rule in PRODUCT_RULES:
        try:
            if rule["condition"](customer) and rule["product"] not in held:
                recommendations.append({
                    "product":   rule["product"],
                    "reason":    rule["reason"],
                    "offer":     rule["offer"],
                    "icon":      rule["icon"],
                    "category":  rule["category"],
                    "score":     round(rule["score"] + random.uniform(-0.05, 0.05), 2),
                })
        except Exception:
            continue

    recommendations.sort(key=lambda x: x["score"], reverse=True)

    if not recommendations:
        recommendations.append({
            "product":  "Sweep FD",
            "reason":   "Idle savings can earn more — Sweep FD auto-invests surplus funds",
            "offer":    "Enable Sweep FD on your savings account — earn FD rates on surplus",
            "icon":     "💹",
            "category": "Savings",
            "score":    0.65,
        })

    return recommendations[:top_n]


def calculate_loyalty_rewards(customer: dict) -> dict:
    """Calculate reward points and triggers for a customer."""
    triggered = []
    total_points = 0
    base_points = int(customer.get("clv_score", 10) * 50)

    for key, reward in REWARD_TRIGGERS.items():
        try:
            if reward["condition"](customer):
                triggered.append({
                    "reward_id": key,
                    "label":     reward["label"],
                    "points":    reward["points"],
                })
                total_points += reward["points"]
        except Exception:
            continue

    total_points += base_points
    tier = "Platinum" if total_points > 15000 else "Gold" if total_points > 8000 else "Silver" if total_points > 3000 else "Bronze"

    return {
        "customer_id":    customer["customer_id"],
        "base_points":    base_points,
        "bonus_triggers": triggered,
        "total_points":   total_points,
        "loyalty_tier":   tier,
        "cashback_value": round(total_points * 0.25, 2),
        "next_tier_gap":  max(0, {"Platinum":15000,"Gold":8000,"Silver":3000,"Bronze":0}
                               .get(tier,0) + 1000 - total_points),
    }


def get_nbp_summary(customers: list) -> dict:
    """Aggregate NBP stats across all customers."""
    product_demand = {}
    for c in customers:
        recs = get_next_best_products(c, top_n=1)
        if recs:
            p = recs[0]["product"]
            product_demand[p] = product_demand.get(p, 0) + 1

    return {
        "product_demand":   dict(sorted(product_demand.items(), key=lambda x: x[1], reverse=True)),
        "total_customers":  len(customers),
        "opportunity_count": sum(product_demand.values()),
    }
