from __future__ import annotations
import calendar
from collections import defaultdict
from datetime import timedelta
from statistics import mean, pstdev
from .models import Txn

WEEKS_PER_MONTH = 4.345


def monthly(txns: list[Txn]) -> list[dict]:
    """Complete months only (>=80% of days covered by the data span)."""
    first, last = min(t.day for t in txns), max(t.day for t in txns)
    agg = defaultdict(lambda: defaultdict(float))
    for t in txns:
        a = agg[(t.day.year, t.day.month)]
        if t.amount > 0:
            a["revenue"] += t.amount
        elif t.category == "loan_repayment":
            a["loan"] += -t.amount
        elif t.category == "owner_draw":
            a["draw"] += -t.amount
        else:
            a["op_out"] += -t.amount
    out = []
    for (y, m) in sorted(agg):
        dim = calendar.monthrange(y, m)[1]
        lo = max(first, first.replace(year=y, month=m, day=1))
        hi = min(last, first.replace(year=y, month=m, day=dim))
        if (hi - lo).days + 1 < 0.8 * dim:
            continue
        a = agg[(y, m)]
        out.append({"month": f"{y}-{m:02d}", "revenue": a["revenue"], "op_out": a["op_out"],
                    "loan": a["loan"], "draw": a["draw"],
                    "op_cash": a["revenue"] - a["op_out"],
                    "net": a["revenue"] - a["op_out"] - a["loan"] - a["draw"]})
    return out


def metrics(txns: list[Txn]) -> dict:
    ms = monthly(txns)
    rev = [m["revenue"] for m in ms]
    tot_rev = sum(rev)
    op_cash = sum(m["op_cash"] for m in ms)
    inflow_named: dict[str, float] = defaultdict(float)
    for t in txns:
        if t.amount > 0 and t.counterparty and t.counterparty != "walk-in":
            inflow_named[t.counterparty] += t.amount
    named_total = sum(inflow_named.values())
    return {
        "months": len(ms),
        "avg_monthly_revenue": mean(rev) if rev else 0.0,
        "revenue_cv": (pstdev(rev) / mean(rev)) if rev and mean(rev) else 0.0,
        "op_margin": op_cash / tot_rev if tot_rev else 0.0,
        "avg_monthly_op_cash": op_cash / len(ms) if ms else 0.0,
        "weekly_repayment_capacity": max(0.0, 0.5 * (op_cash / len(ms)) / WEEKS_PER_MONTH) if ms else 0.0,
        "top_customer_share": (max(inflow_named.values()) / named_total) if named_total else 0.0,
        "cash_share": sum(t.amount for t in txns if t.amount > 0 and t.channel == "cash") / tot_rev if tot_rev else 0.0,
        "monthly": ms,
    }


def weekly_series(txns: list[Txn]) -> list[tuple]:
    """(week_start, inflow, outflow). Drops a partial first week and a last week that stops before Saturday."""
    b: dict = {}
    for t in txns:
        ws = t.day - timedelta(days=t.day.weekday())
        v = b.setdefault(ws, [0.0, 0.0])
        v[0 if t.amount > 0 else 1] += abs(t.amount)
    rows = [(w, v[0], v[1]) for w, v in sorted(b.items())]
    if min(t.day for t in txns).weekday() > 0:
        rows = rows[1:]
    if max(t.day for t in txns).weekday() < 5:
        rows = rows[:-1]
    return rows
