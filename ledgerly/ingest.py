from __future__ import annotations
import csv
from math import isfinite
from datetime import date
from .models import Txn
from .security import sanitize_memo

RULES = [
    ("loan_repayment", ("loan", "repayment")),
    ("owner_draw", ("owner", "personal", "withdrawal")),
    ("supplier", ("supplier", "restock", "wholesale")),
    ("rent", ("rent",)),
    ("wages", ("wage", "salary")),
    ("transport", ("transport", "logistics", "dispatch", "fuel")),
]


def categorize(memo: str, amount: float) -> str:
    if amount > 0:
        return "sales"
    m = memo.lower()
    for cat, keys in RULES:
        if any(k in m for k in keys):
            return cat
    return "other"


def load_csv(path: str) -> tuple[list[Txn], dict]:
    """Columns: date,amount,description,channel,counterparty. Returns (txns, data_quality)."""
    txns, bad, injected = [], 0, 0
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                d = date.fromisoformat(row["date"].strip())
                amt = float(row["amount"].replace(",", ""))
                if not isfinite(amt):
                    raise ValueError("nonfinite amount")
            except (ValueError, KeyError, AttributeError):
                bad += 1
                continue
            memo, flagged = sanitize_memo(row.get("description", ""))
            injected += flagged
            txns.append(Txn(d, amt, categorize(memo, amt), row.get("channel", "cash").strip() or "cash",
                            row.get("counterparty", "").strip(), memo))
    txns.sort(key=lambda t: t.day)
    return txns, {"rows_loaded": len(txns), "rows_rejected": bad, "injection_flags": injected}
