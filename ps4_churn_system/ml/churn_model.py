"""
PS4 - ML Churn Prediction Model
XGBoost + SHAP for churn probability scoring and explainability
"""

import pandas as pd
import numpy as np
import pickle, os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    from sklearn.ensemble import GradientBoostingClassifier
    XGB_AVAILABLE = False

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

FEATURE_COLS = [
    "tenure_years", "monthly_salary", "num_products",
    "txn_freq_monthly", "avg_ticket_size", "upi_txns_monthly",
    "app_logins_monthly", "netbanking_sessions", "days_since_login",
    "cross_bank_outflow", "complaints_6m", "csat_score",
    "fd_maturing_days", "loan_overdue_days", "credit_util_pct", "clv_score"
]

FEATURE_LABELS = {
    "days_since_login":    "Inactive on app",
    "cross_bank_outflow":  "Funds moved to competitor",
    "complaints_6m":       "Repeated complaints",
    "csat_score":          "Low satisfaction score",
    "txn_freq_monthly":    "Low transaction activity",
    "credit_util_pct":     "High credit utilisation",
    "tenure_years":        "Short tenure",
    "num_products":        "Few products held",
    "app_logins_monthly":  "Low app engagement",
    "upi_txns_monthly":    "Reduced UPI usage",
}

MODEL_PATH = "ml/churn_model.pkl"
SCALER_PATH = "ml/scaler.pkl"


def train_model(df: pd.DataFrame):
    X = df[FEATURE_COLS].fillna(0)
    y = df["churn_label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc  = scaler.transform(X_test)

    if XGB_AVAILABLE:
        model = xgb.XGBClassifier(
            n_estimators=150, max_depth=5, learning_rate=0.08,
            use_label_encoder=False, eval_metric="logloss",
            random_state=42, verbosity=0
        )
    else:
        from sklearn.ensemble import GradientBoostingClassifier
        model = GradientBoostingClassifier(
            n_estimators=150, max_depth=5, learning_rate=0.08, random_state=42
        )

    model.fit(X_train_sc, y_train)

    y_pred  = model.predict(X_test_sc)
    y_proba = model.predict_proba(X_test_sc)[:, 1]
    auc     = roc_auc_score(y_test, y_proba)
    print(f"✅ Model trained | AUC: {auc:.3f}")
    print(classification_report(y_test, y_pred))

    os.makedirs("ml", exist_ok=True)
    with open(MODEL_PATH, "wb") as f: pickle.dump(model, f)
    with open(SCALER_PATH, "wb") as f: pickle.dump(scaler, f)

    return model, scaler, auc


def load_model():
    with open(MODEL_PATH, "rb") as f: model  = pickle.load(f)
    with open(SCALER_PATH, "rb") as f: scaler = pickle.load(f)
    return model, scaler


def score_customers(df: pd.DataFrame, model=None, scaler=None):
    """Score all customers and return enriched DataFrame."""
    if model is None or scaler is None:
        model, scaler = load_model()

    X = df[FEATURE_COLS].fillna(0)
    X_sc = scaler.transform(X)
    proba = model.predict_proba(X_sc)[:, 1]

    df = df.copy()
    df["churn_probability"] = proba.round(3)

    # Risk tier
    def tier(p):
        if p > 0.80: return "Critical"
        if p > 0.65: return "High"
        if p > 0.40: return "Medium"
        return "Low"

    df["risk_tier"] = df["churn_probability"].apply(tier)

    # Churn horizon
    def horizon(p):
        if p > 0.80: return "30 days"
        if p > 0.65: return "60 days"
        return "90 days"

    df["churn_horizon"] = df["churn_probability"].apply(horizon)

    # Priority index = CLV × churn probability
    df["priority_index"] = (df["clv_score"] * df["churn_probability"]).round(2)

    # Top 3 churn reasons via simple rule-based SHAP proxy
    df["top_reasons"] = df.apply(_top_reasons, axis=1)

    # Queue assignment
    def queue(p):
        if p > 0.65: return "Active Outreach"
        if p > 0.40: return "Watchlist"
        return "Healthy"

    df["queue"] = df["churn_probability"].apply(queue)

    return df


def _top_reasons(row) -> str:
    """Rule-based churn reason extraction (SHAP proxy for demo)."""
    reasons = []
    if row["days_since_login"] > 60:      reasons.append("Inactive on app")
    if row["cross_bank_outflow"] == 1:     reasons.append("Funds moved to competitor")
    if row["complaints_6m"] >= 3:          reasons.append("Repeated complaints")
    if row["csat_score"] < 2.5:            reasons.append("Low satisfaction score")
    if row["txn_freq_monthly"] < 3:        reasons.append("Low transaction activity")
    if row["credit_util_pct"] > 85:        reasons.append("High credit utilisation")
    if row["num_products"] == 1:           reasons.append("Single product holder")
    if row["tenure_years"] < 1:            reasons.append("New customer at risk")
    if row["app_logins_monthly"] == 0:     reasons.append("Zero app logins")
    return " | ".join(reasons[:3]) if reasons else "General inactivity"


def get_segment_stats(df: pd.DataFrame) -> dict:
    seg = df.groupby("segment").agg(
        count=("customer_id", "count"),
        avg_churn=("churn_probability", "mean"),
        avg_clv=("clv_score", "mean")
    ).reset_index()
    return seg.to_dict(orient="records")
