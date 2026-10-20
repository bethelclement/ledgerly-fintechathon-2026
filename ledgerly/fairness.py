"""Portfolio-level fairness monitoring. Gender is used ONLY here, for aggregate reporting."""
from __future__ import annotations
from collections import defaultdict


def approval_rates(results: list[tuple[str, bool]]) -> dict[str, float]:
    tot, ok = defaultdict(int), defaultdict(int)
    for group, approved in results:
        tot[group] += 1
        ok[group] += bool(approved)
    return {g: ok[g] / tot[g] for g in tot}


def disparate_impact(results: list[tuple[str, bool]], protected: str, reference: str) -> float | None:
    r = approval_rates(results)
    if protected not in r or reference not in r or r[reference] == 0:
        return None
    return r[protected] / r[reference]      # < 0.80 breaches the four-fifths rule
