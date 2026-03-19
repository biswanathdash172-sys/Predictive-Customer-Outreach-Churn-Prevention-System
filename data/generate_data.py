"""
PS4 - Synthetic Customer Data Generator
Generates realistic bank customer data for churn prediction demo
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

random.seed(42)
np.random.seed(42)

FIRST_NAMES = ["Aarav","Priya","Rohit","Sneha","Vikram","Ananya","Karan","Pooja",
               "Arjun","Divya","Suresh","Meera","Raj","Kavita","Amit","Nisha",
               "Deepak","Sunita","Rahul","Lakshmi","Sanjay","Geeta","Arun","Usha"]
LAST_NAMES  = ["Sharma","Patel","Singh","Kumar","Gupta","Verma","Joshi","Nair",
               "Reddy","Iyer","Mehta","Chopra","Das","Rao","Shah","Mishra"]
CITIES      = ["Mumbai","Delhi","Bengaluru","Chennai","Hyderabad","Pune","Kolkata",
               "Ahmedabad","Jaipur","Lucknow","Bhubaneswar","Surat","Nagpur","Indore"]
PRODUCTS    = ["Savings Account","Fixed Deposit","Recurring Deposit","Credit Card",
               "Home Loan","Personal Loan","Demat Account","Insurance"]

def generate_customers(n=300):
    records = []
    for i in range(n):
        # --- core profile ---
        name        = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        age         = random.randint(22, 65)
        city        = random.choice(CITIES)
        tenure_yrs  = round(random.uniform(0.5, 15), 1)
        salary      = random.randint(25000, 250000)

        # --- product holdings ---
        num_products   = random.randint(1, 5)
        held_products  = random.sample(PRODUCTS, num_products)

        # --- transaction behaviour ---
        txn_freq_monthly = random.randint(0, 40)
        avg_ticket_size  = random.randint(200, 50000)
        upi_txns_monthly = random.randint(0, 60)

        # --- digital engagement ---
        app_logins_monthly  = random.randint(0, 30)
        netbanking_sessions = random.randint(0, 20)
        days_since_login    = random.randint(0, 180)

        # --- competitive signals ---
        cross_bank_outflow = random.choice([0, 0, 0, 1])  # 25% chance
        complaints_6m      = random.randint(0, 6)
        csat_score         = round(random.uniform(1.0, 5.0), 1)

        # --- product lifecycle ---
        fd_maturing_days   = random.choice([None, random.randint(1, 90)])
        loan_overdue_days  = random.randint(0, 30)
        credit_util_pct    = round(random.uniform(10, 95), 1)

        # --- churn label logic (probabilistic) ---
        churn_score = 0.0
        if days_since_login > 60:       churn_score += 0.25
        if cross_bank_outflow:          churn_score += 0.30
        if complaints_6m >= 3:          churn_score += 0.20
        if txn_freq_monthly < 3:        churn_score += 0.15
        if csat_score < 2.5:            churn_score += 0.20
        if tenure_yrs < 1:              churn_score += 0.10
        if credit_util_pct > 85:        churn_score += 0.10
        churn_score += np.random.normal(0, 0.08)
        churn_score  = float(np.clip(churn_score, 0.0, 1.0))

        # segment label
        if cross_bank_outflow:
            segment = "Price-Sensitive"
        elif days_since_login > 60 and txn_freq_monthly < 3:
            segment = "Disengaged"
        elif complaints_6m >= 3:
            segment = "Complaint-Driven"
        elif fd_maturing_days and fd_maturing_days < 30:
            segment = "Product Maturity"
        else:
            segment = "Life-Event"

        # CLV proxy
        clv = round((salary * 0.05 * tenure_yrs * num_products) / 1000, 1)

        records.append({
            "customer_id":          f"UBI{10000 + i}",
            "name":                 name,
            "age":                  age,
            "city":                 city,
            "tenure_years":         tenure_yrs,
            "monthly_salary":       salary,
            "num_products":         num_products,
            "products_held":        ", ".join(held_products),
            "txn_freq_monthly":     txn_freq_monthly,
            "avg_ticket_size":      avg_ticket_size,
            "upi_txns_monthly":     upi_txns_monthly,
            "app_logins_monthly":   app_logins_monthly,
            "netbanking_sessions":  netbanking_sessions,
            "days_since_login":     days_since_login,
            "cross_bank_outflow":   cross_bank_outflow,
            "complaints_6m":        complaints_6m,
            "csat_score":           csat_score,
            "fd_maturing_days":     fd_maturing_days if fd_maturing_days else 999,
            "loan_overdue_days":    loan_overdue_days,
            "credit_util_pct":      credit_util_pct,
            "churn_label":          int(churn_score > 0.55),
            "segment":              segment,
            "clv_score":            clv,
            "preferred_channel":    random.choice(["WhatsApp","Push","SMS","Email"]),
            "preferred_language":   random.choice(["English","Hindi","Telugu","Tamil","Odia","Marathi"]),
        })

    df = pd.DataFrame(records)
    df.to_csv("data/customers.csv", index=False)
    print(f"✅ Generated {n} synthetic customers → data/customers.csv")
    return df

if __name__ == "__main__":
    generate_customers()
