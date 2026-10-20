"""Cash-flow credit passport. Inputs are TRANSACTION BEHAVIOUR ONLY.
No gender, ethnicity, religion, age or location enters the score."""
from __future__ import annotations
from . import analysis
from .models import Txn

TIPS = {
    "history": "Keep every sale and expense recorded for 12 months; longer history raises trust.",
    "stability": "Smooth revenue with repeat customers, pre-orders or subscriptions.",
    "margin": "Review supplier prices and low-margin lines to widen your operating margin.",
    "growth": "Grow monthly sales; even steady 5% growth lifts this factor.",
    "concentration": "Avoid depending on one or two customers for most of your sales.",
    "coverage": "Keep operating cash well above loan repayments before taking new debt.",
    "discipline": "Repay on time every month and keep the repayment records in the app.",
}


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def grade(score: float) -> str:
    return "A" if score >= 75 else "B" if score >= 60 else "C" if score >= 45 else "D"


def build_passport(txns: list[Txn]) -> dict:
    mt = analysis.metrics(txns)
    ms = mt["monthly"]
    rev = [m["revenue"] for m in ms]
    f = []

    def add(key, label, weight, s, why):
        s = clamp(s)
        f.append({"key": key, "label": label, "weight": weight, "score01": round(s, 3),
                  "points": round(weight * s, 1), "explanation": why})

    add("history", "Records history", 10, mt["months"] / 12, f"{mt['months']} complete months of records.")
    add("stability", "Revenue stability", 20, 1 - mt["revenue_cv"] / 0.6,
        f"Monthly revenue varies by {mt['revenue_cv']:.0%} (lower is steadier).")
    add("margin", "Operating margin", 20, mt["op_margin"] / 0.20,
        f"Operating margin is {mt['op_margin']:.0%} before loan repayments and owner draws.")
    if len(rev) >= 6:
        g = sum(rev[-3:]) / max(1.0, sum(rev[-6:-3])) - 1
    else:
        g = 0.0
    add("growth", "Sales trend", 10, 0.5 + g * 2.5, f"Last 3 months vs previous 3: {g:+.0%}.")
    t = mt["top_customer_share"]
    add("concentration", "Customer spread", 10, 1 - (t - 0.10) / 0.30,
        f"Largest named customer is {t:.0%} of named sales.")
    loan = sum(m["loan"] for m in ms)
    if loan > 0:
        dscr = sum(m["op_cash"] for m in ms) / loan
        add("coverage", "Debt-service coverage", 20, (dscr - 1) / 2, f"Operating cash covers repayments {dscr:.1f}x.")
    else:
        add("coverage", "Debt-service coverage", 20, 0.7, "No recorded debt service (neutral).")
    paid = [m for m in ms if m["loan"] > 0]
    if paid:
        first = next(i for i, m in enumerate(ms) if m["loan"] > 0)
        span = len(ms) - first
        add("discipline", "Repayment discipline", 10, len(paid) / span,
            f"Repayments recorded in {len(paid)} of {span} months since the first one.")
    else:
        add("discipline", "Repayment discipline", 10, 0.5, "No repayment history (neutral).")

    score = round(sum(x["points"] for x in f), 1)
    weakest = sorted(f, key=lambda x: x["weight"] * (1 - x["score01"]), reverse=True)[:2]
    return {"score": score, "grade": grade(score), "factors": f,
            "improve": [TIPS[w["key"]] for w in weakest],
            "weekly_repayment_capacity": mt["weekly_repayment_capacity"], "metrics": {k: v for k, v in mt.items() if k != "monthly"}}
