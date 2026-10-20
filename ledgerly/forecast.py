from __future__ import annotations
from collections import defaultdict
from datetime import timedelta
from statistics import mean
from .models import WeekForecast


def month_factors(series: list[tuple], idx: int) -> dict[int, float]:
    overall = mean(s[idx] for s in series)
    by_m = defaultdict(list)
    for s in series:
        by_m[s[0].month].append(s[idx])
    # shrink 30% toward 1.0: one year of history is thin evidence of seasonality
    return {m: 0.7 * (mean(v) / overall) + 0.3 if overall else 1.0 for m, v in by_m.items()}


def _seasonal_naive(series, weeks):
    """Same weeks one year earlier (3-week centred average), scaled by recent trend if 60+ weeks exist."""
    n = len(series)
    ref = n - 52
    trend = 1.0
    if n >= 60:
        a, b = sum(s[1] for s in series[-8:]), sum(s[1] for s in series[-60:-52])
        trend = min(1.25, max(0.8, a / b)) if b else 1.0

    def at(j, idx):
        lo, hi = max(0, j - 1), min(n - 1, j + 1)
        return mean(series[k][idx] for k in range(lo, hi + 1))
    return [(at(ref + k, 1) * trend, at(ref + k, 2) * trend) for k in range(weeks)]


def forecast(series: list[tuple], opening_balance: float, weeks: int = 13,
             inflow_mult: float = 1.0, outflow_mult: float = 1.0) -> list[WeekForecast]:
    """52+ weeks of history: seasonal-naive (same weeks last year). Less: deseasonalised level x month factor.
    Transparent by design, so a lender or owner can audit every number."""
    start, bal, out = series[-1][0] + timedelta(weeks=1), opening_balance, []
    if len(series) >= 52:
        pairs = _seasonal_naive(series, weeks)
    else:
        fi, fo = month_factors(series, 1), month_factors(series, 2)
        tail = series[-8:]
        li = mean(s[1] / fi.get(s[0].month, 1.0) for s in tail)
        lo = mean(s[2] / fo.get(s[0].month, 1.0) for s in tail)
        pairs = []
        for k in range(weeks):
            m = (start + timedelta(weeks=k)).month
            pairs.append((li * fi.get(m, 1.0), lo * fo.get(m, 1.0)))
    for k, (i, o) in enumerate(pairs):
        i, o = i * inflow_mult, o * outflow_mult
        bal += i - o
        out.append(WeekForecast(start + timedelta(weeks=k), i, o, bal))
    return out


def summarize(fc: list[WeekForecast], opening_balance: float) -> dict:
    low = min(fc, key=lambda w: w.closing)
    buffer = 2 * mean(w.outflow for w in fc)          # safety buffer: two weeks of outflows
    neg = next((w for w in fc if w.closing < 0), None)
    return {
        "min_balance": low.closing, "min_week": low.week_start.isoformat(),
        "first_negative_week": neg.week_start.isoformat() if neg else None,
        "safety_buffer": buffer,
        "need": max(0.0, buffer - low.closing),
        "end_balance": fc[-1].closing, "opening_balance": opening_balance,
    }


def scenarios(series, opening_balance, weeks=13) -> dict:
    cfg = {"base": (1.0, 1.0), "downside": (0.8, 1.0), "upside": (1.1, 1.0)}
    res = {}
    for name, (im, om) in cfg.items():
        fc = forecast(series, opening_balance, weeks, im, om)
        res[name] = {"weeks": fc, "summary": summarize(fc, opening_balance)}
    return res
