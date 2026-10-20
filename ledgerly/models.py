from __future__ import annotations
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Txn:
    day: date
    amount: float          # + inflow, - outflow (NGN)
    category: str          # sales, supplier, rent, wages, transport, loan_repayment, owner_draw, other
    channel: str           # pos, mobile_money, cash
    counterparty: str
    memo: str


@dataclass(frozen=True)
class Business:
    name: str
    sector: str
    city: str
    # Used ONLY for portfolio-level impact reporting. Never an input to scoring or matching.
    owner_gender: str = "undisclosed"


@dataclass(frozen=True)
class WeekForecast:
    week_start: date
    inflow: float
    outflow: float
    closing: float
