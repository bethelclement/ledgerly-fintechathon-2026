"""Financing-option matching. The catalogue is ILLUSTRATIVE (synthetic terms) for the demo;
production would pull live lender terms through partner APIs."""
from __future__ import annotations
from dataclasses import dataclass
from math import ceil, isfinite


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    min_score: float
    apr: float
    fee_pct: float
    term_weeks: float
    max_multiple: float        # x average monthly revenue
    max_abs: float | None = None
    collateral: bool = False
    days_to_fund: int = 3


CATALOGUE = [
    Product("BANK-WC", "Bank working-capital loan", 70, 0.28, 0.010, 16, 1.0, None, True, 10),
    Product("FIN-CF", "Fintech cash-flow loan", 55, 0.36, 0.020, 12, 0.6, None, False, 2),
    Product("MFB-GRP", "Microfinance group loan", 40, 0.30, 0.020, 24, 0.5, None, False, 7),
    Product("SUP-NET30", "Supplier credit (2/10 net 30)", 45, 0.0, 0.020, 2.9, 0.5, None, False, 0),
    Product("MM-OD", "Mobile-money overdraft", 35, 0.60, 0.030, 4, 0.1, 150_000, False, 0),
]


def evaluate(p: Product, amount: float, capacity_weekly: float) -> dict:
    if not isfinite(amount) or amount <= 0 or not isfinite(capacity_weekly) or capacity_weekly < 0:
        raise ValueError("amount must be positive and capacity nonnegative, both finite")
    interest = amount * p.apr * p.term_weeks / 52
    fees = amount * p.fee_pct
    cost = interest + fees
    weekly = (amount + cost) / p.term_weeks
    return {"product_id": p.id, "name": p.name, "amount": round(amount), "term_weeks": p.term_weeks,
            "total_cost": round(cost), "annualized_cost_rate": round(cost / amount * 52 / p.term_weeks, 3),
            "cost_method": "simple annualized total cost; not amortizing APR or IRR",
            "weekly_payment": round(weekly), "affordable": weekly <= capacity_weekly,
            "days_to_fund": p.days_to_fund, "collateral_required": p.collateral}


def match(need: float, score: float, avg_monthly_revenue: float, capacity_weekly: float,
          has_collateral: bool = False) -> dict:
    if any(not isfinite(x) or x < 0 for x in (need, score, avg_monthly_revenue, capacity_weekly)):
        raise ValueError("financing inputs must be finite and nonnegative")
    if need <= 0:
        return {"need": 0, "offers": [], "recommended_offer": None, "note": "No financing needed: cash stays above the safety buffer."}
    need = ceil(need / 10_000) * 10_000
    offers = []
    for p in CATALOGUE:
        if score < p.min_score or (p.collateral and not has_collateral):
            continue
        cap = p.max_multiple * avg_monthly_revenue
        if p.max_abs:
            cap = min(cap, p.max_abs)
        amount = min(need, cap)
        if amount <= 0:
            continue
        o = evaluate(p, amount, capacity_weekly)
        o["covers_need"] = amount >= need
        offers.append(o)
    rank = lambda o: (0 if o["affordable"] and o["covers_need"] else 1 if o["affordable"] else 2, o["annualized_cost_rate"])
    offers.sort(key=rank)
    for o in offers:
        o["why"] = ("Covers the gap and fits your repayment capacity" if o["affordable"] and o["covers_need"]
                    else "Affordable but only covers part of the gap" if o["affordable"]
                    else "Weekly payment exceeds your repayment capacity")
    safe = [o for o in offers if o["affordable"] and o["covers_need"]]
    recommended = min(safe, key=lambda o: (o["annualized_cost_rate"], o["total_cost"], o["product_id"])) if safe else None
    note = "" if recommended else ("No eligible product at this score." if not offers else
        "No affordable offer covers the full gap. No application or disbursement will be attempted; reduce the request or improve cash flow.")
    return {"need": need, "offers": offers, "recommended_offer": recommended, "note": note}
