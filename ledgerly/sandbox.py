"""Simulated accounts and lender. NO real money ever moves. Every operation is logged as evidence."""
from __future__ import annotations
import json
from math import isfinite
from datetime import datetime, timezone
from .security import mask_pii


class SandboxEnv:
    def __init__(self, opening_balance: float, log_path: str | None = None, disbursement_cap: float = 5_000_000):
        self.balance, self.cap, self.log_path = opening_balance, disbursement_cap, log_path
        self.ops: list[dict] = []
        self._idem: dict[str, dict] = {}
        self._apps: dict[str, dict] = {}
        if log_path:
            open(log_path, "w").close()

    def _log(self, op: str, params: dict, result: dict) -> dict:
        e = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sandbox": True, "op": op,
             "params": json.loads(mask_pii(json.dumps(params, default=str))), "result": result}
        self.ops.append(e)
        if self.log_path:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(e) + "\n")
        return e

    def _once(self, key, op, params, fn):
        if key in self._idem:
            return {**self._idem[key], "replayed": True}
        res = fn()
        self._idem[key] = res
        self._log(op, {**params, "idempotency_key": key}, res)
        return res

    def notify_owner(self, message: str, key: str) -> dict:
        return self._once(key, "notify_owner", {"channel": "sms_sandbox", "message": message},
                          lambda: {"status": "SENT"})

    def apply(self, product_id: str, amount: float, score: float, min_score: float, key: str) -> dict:
        def run():
            ref = f"SBX-{len(self._apps) + 1:04d}"
            ok = isfinite(amount) and amount > 0 and score >= min_score and amount <= self.cap
            self._apps[ref] = {"amount": amount, "approved": ok, "disbursed": False}
            return {"ref": ref, "status": "APPROVED" if ok else "DECLINED", "product_id": product_id, "amount": amount}
        return self._once(key, "lender_application", {"product_id": product_id, "amount": amount}, run)

    def disburse(self, ref: str, key: str) -> dict:
        def run():
            a = self._apps.get(ref)
            if not a or not a["approved"] or a["disbursed"] or a["amount"] > self.cap:
                return {"ref": ref, "status": "REFUSED"}
            a["disbursed"] = True
            self.balance += a["amount"]
            return {"ref": ref, "status": "DISBURSED", "new_balance": self.balance}
        return self._once(key, "disbursement", {"ref": ref}, run)
