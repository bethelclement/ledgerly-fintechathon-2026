"""Ledgerly agent: plans -> tiered, audited tool execution -> plain-language report.
The planner may be rule-based (offline) or an LLM; either way the plan is VALIDATED against the tool
registry, dependencies and permission tiers, so a model can never exceed what the policy allows."""
from __future__ import annotations
from typing import Callable
from math import isfinite
import re
from . import analysis, financing, forecast as fc, passport
from .models import Business, Txn
from .sandbox import SandboxEnv
from .security import AuditLog, Consent, PermissionDenied, Policy, Tier

TOOLS: dict[str, tuple[Tier, tuple[str, ...]]] = {
    "forecast": (Tier.READ, ()),
    "passport": (Tier.READ, ()),
    "alerts": (Tier.READ, ("forecast", "passport")),
    "match": (Tier.READ, ("forecast", "passport")),
    "pack": (Tier.PREPARE, ("match",)),
    "notify": (Tier.ACT_LOW, ("alerts",)),
    "submit": (Tier.ACT_MONEY, ("pack",)),
    "disburse": (Tier.ACT_MONEY, ("submit",)),
}
naira = lambda x: f"\u20a6{x:,.0f}"


def route(goal: str) -> list[str]:
    g = goal.lower()
    steps = ["forecast", "passport", "alerts"]
    if any(k in g for k in ("loan", "financ", "borrow", "fund", "capital", "stock", "restock", "afford")):
        steps += ["match", "pack"]
    if any(k in g for k in ("apply", "submit", "take the", "get the")):
        steps += ["notify", "submit"]
    if "disburse" in g or re.search(r"\bfund\b.*\bsandbox\b", g):
        steps.append("disburse")
    if "alert" in g or "notify" in g:
        steps.append("notify")
    return steps


def resolve(steps: list[str]) -> list[str]:
    out: list[str] = []

    def visit(s):
        if s not in TOOLS:
            return                                  # unknown tool from a planner is dropped
        for d in TOOLS[s][1]:
            visit(d)
        if s not in out:
            out.append(s)
    for s in steps:
        visit(s)
    return out


class Agent:
    def __init__(self, business: Business, txns: list[Txn], opening_balance: float, consent: Consent,
                 policy: Policy | None = None, env: SandboxEnv | None = None, audit: AuditLog | None = None,
                 llm_planner: Callable[[str, list[str]], list[str]] | None = None,
                 approver: Callable[[str, dict], bool] | None = None):
        if not txns:
            raise ValueError("at least one transaction is required")
        if not isfinite(opening_balance) or opening_balance < 0:
            raise ValueError("opening_balance must be finite and nonnegative")
        self.b, self.txns, self.opening = business, txns, opening_balance
        self.consent, self.policy = consent, policy or Policy()
        self.env = env or SandboxEnv(opening_balance)
        self.audit = audit or AuditLog()
        self.llm_planner, self.approver = llm_planner, approver
        self.ctx: dict = {}

    # ---- planning
    def plan(self, goal: str) -> list[str]:
        steps = route(goal)
        if self.llm_planner:
            try:
                steps = self.llm_planner(goal, list(TOOLS)) or steps
            except Exception as e:                    # model failure never blocks the safe default
                self.audit.record("agent", "planner_error", {"error": str(e)})
        return resolve(steps)

    # ---- tools
    def _t_forecast(self):
        series = analysis.weekly_series(self.txns)
        self.ctx["scen"] = fc.scenarios(series, self.opening)

    def _t_passport(self):
        if not self.consent.allows("credit_assessment"):
            raise PermissionDenied("owner has not consented to credit_assessment")
        self.ctx["passport"] = passport.build_passport(self.txns)

    def _t_alerts(self):
        s, p, a = self.ctx["scen"], self.ctx["passport"], []
        d, base = s["downside"]["summary"], s["base"]["summary"]
        if base["first_negative_week"]:
            a.append({"severity": "high", "msg": f"Cash goes negative in the week of {base['first_negative_week']} even in the base case."})
        if d["need"] > 0:
            a.append({"severity": "high" if d["first_negative_week"] else "medium",
                      "msg": f"If sales are 20% weaker, cash could fall to {naira(d['min_balance'])} in the week of {d['min_week']}, "
                             f"below your two-week buffer of {naira(d['safety_buffer'])}."})
        m = p["metrics"]
        if m["top_customer_share"] > 0.30:
            a.append({"severity": "medium", "msg": f"One customer is {m['top_customer_share']:.0%} of named sales."})
        if m["cash_share"] > 0.40:
            a.append({"severity": "low", "msg": f"{m['cash_share']:.0%} of sales are cash entries; digital records strengthen your passport."})
        self.ctx["alerts"] = a

    def _t_match(self):
        p, d = self.ctx["passport"], self.ctx["scen"]["downside"]["summary"]
        need = self.ctx["requested_amount"] if self.ctx.get("requested_amount") is not None else d["need"]
        self.ctx["match"] = financing.match(need, p["score"], p["metrics"]["avg_monthly_revenue"],
                                            p["weekly_repayment_capacity"], self.ctx.get("has_collateral", False))

    def _t_pack(self):
        if not self.consent.allows("share_with_lender"):
            raise PermissionDenied("owner has not consented to share_with_lender")
        p, m = self.ctx["passport"], self.ctx["match"]
        self.ctx["pack"] = {
            "business": {"name": self.b.name, "sector": self.b.sector, "city": self.b.city},
            "passport": {"score": p["score"], "grade": p["grade"],
                         "factors": [{k: f[k] for k in ("label", "points", "explanation")} for f in p["factors"]]},
            "forecast": {k: (round(v) if isinstance(v, float) else v) for k, v in self.ctx["scen"]["downside"]["summary"].items()},
            "request": m["recommended_offer"],
            "excluded_from_pack": ["raw transactions", "customer identities", "phone and account numbers"],
        }

    def _t_notify(self):
        hi = [a["msg"] for a in self.ctx["alerts"] if a["severity"] in ("high", "medium")]
        r = self.env.notify_owner(" | ".join(hi) or "No cash risks detected.", key=f"notify-{self.b.name}")
        self.ctx["notify"] = r

    def _t_submit(self):
        offer = self.ctx["pack"]["request"]
        if not offer:
            self.ctx["submit"] = {"status": "SKIPPED", "reason": self.ctx["match"]["note"] or "no safe recommended offer"}
            return
        prod = next(x for x in financing.CATALOGUE if x.id == offer["product_id"])
        a = self.env.apply(prod.id, offer["amount"], self.ctx["passport"]["score"], prod.min_score,
                           key=f"apply-{self.b.name}-{prod.id}-{offer['amount']}")
        self.ctx["submit"] = {"application": a}

    def _t_disburse(self):
        a = (self.ctx.get("submit") or {}).get("application")
        if not a or a["status"] != "APPROVED":
            self.ctx["disburse"] = {"status": "SKIPPED", "reason": "no approved sandbox application"}
            return
        self.ctx["disburse"] = self.env.disburse(a["ref"], key=f"disb-{a['ref']}")

    # ---- execution
    def run(self, goal: str, requested_amount: float | None = None, has_collateral: bool = False) -> dict:
        if requested_amount is not None and (not isfinite(requested_amount) or requested_amount < 0):
            raise ValueError("requested_amount must be finite and nonnegative")
        self.ctx = {"requested_amount": requested_amount, "has_collateral": has_collateral}
        steps = self.plan(goal)
        self.audit.record("owner", "goal", {"goal": goal, "plan": steps})
        status, pending = "complete", None
        for name in steps:
            tier = TOOLS[name][0]
            try:
                self.policy.check(name, tier)
                if (tier == Tier.ACT_MONEY or self.policy.needs_approval(tier)) and (self.ctx.get("pack") or {}).get("request"):
                    preview = {"tool": name, "offer": (self.ctx.get("pack") or {}).get("request"),
                               "sandbox": True, "application": (self.ctx.get("submit") or {}).get("application") }
                    self.audit.record("agent", "approval_requested", preview)
                    if not (self.approver and self.approver(name, preview)):
                        self.audit.record("agent", "paused_pending_approval", {"tool": name})
                        status, pending = "pending_approval", name
                        break
                    self.audit.record("owner", "approved", {"tool": name})
                getattr(self, "_t_" + name)()
                self.audit.record("agent", "tool_ok", {"tool": name, "tier": int(tier)})
            except PermissionDenied as e:
                self.audit.record("agent", "denied", {"tool": name, "reason": str(e)})
                status, pending = "denied", name
                break
        return self._report(goal, steps, status, pending)

    def _report(self, goal, steps, status, pending) -> dict:
        c = self.ctx
        rep = {"goal": goal, "plan": steps, "status": status, "pending": pending,
               "passport": c.get("passport"), "alerts": c.get("alerts", []), "match": c.get("match"),
               "pack": c.get("pack"), "submit": c.get("submit"), "disburse": c.get("disburse"),
               "audit_chain_valid": self.audit.verify()}
        if "scen" in c:
            rep["forecast"] = {k: v["summary"] for k, v in c["scen"].items()}
        rep["summary"] = self._narrate(rep)
        return rep

    def _narrate(self, r) -> str:
        L = []
        p = r.get("passport")
        if p:
            L.append(f"Your cash-flow credit passport: {p['score']}/100 (grade {p['grade']}). Biggest levers: " + " ".join(p["improve"]))
        for a in r["alerts"]:
            L.append(f"[{a['severity'].upper()}] {a['msg']}")
        m = r.get("match")
        if m:
            if not m["recommended_offer"]:
                L.append(m["note"] or "No safe recommended offer.")
            else:
                o = m["recommended_offer"]
                L.append(f"Best fit for a {naira(m['need'])} gap: {o['name']} {naira(o['amount'])} over {o['term_weeks']:g} weeks, "
                         f"total cost {naira(o['total_cost'])} (simple annualized cost {o['annualized_cost_rate']:.0%}, not APR/IRR), "
                         f"about {naira(o['weekly_payment'])}/week. {o['why']}.")
        if r["status"] == "pending_approval":
            L.append(f"Waiting for explicit approval of {r['pending']} in the sandbox. Application and disbursement each need separate approval.")
        elif r.get("submit"):
            L.append(f"Sandbox result: {r['submit']}")
        if r.get("disburse"):
            L.append(f"Sandbox disbursement: {r['disburse']}")
        return "\n".join(L)
