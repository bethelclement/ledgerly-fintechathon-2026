"""Security & compliance layer: permission tiers, approvals, PII masking,
prompt-injection screening, consent, and a tamper-evident audit log."""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum


class Tier(IntEnum):
    READ = 0        # analyse data already consented
    PREPARE = 1     # build drafts / packs (no external effect)
    ACT_LOW = 2     # reversible external effects (owner notifications)
    ACT_MONEY = 3   # financial commitments: ALWAYS needs human approval


class PermissionDenied(Exception):
    pass


EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"\b(?:\+?234|0)[789][01]\d{8}\b")
LONGNUM = re.compile(r"\b\d{10,11}\b")      # NUBAN account / BVN-like ids
INJECTION = re.compile(
    r"(ignore (all |any )?(previous|prior|above)|disregard .{0,30}instructions|system prompt|"
    r"you are now|transfer (all|everything)|approve (this|the) (loan|application)|send .{0,40}to account)",
    re.I,
)


def mask_pii(text: str) -> str:
    text = EMAIL.sub("[email]", text)
    text = PHONE.sub("[phone]", text)
    return LONGNUM.sub("[id]", text)


def sanitize_memo(memo: str) -> tuple[str, bool]:
    """Treat transaction memos as DATA. Instruction-like text is neutralised and flagged."""
    if INJECTION.search(memo):
        return "[redacted: instruction-like text in data field]", True
    return mask_pii(memo), False


@dataclass(frozen=True)
class Consent:
    purposes: frozenset
    granted_at: str = "2026-10-18"

    def allows(self, purpose: str) -> bool:
        return purpose in self.purposes


class Policy:
    def __init__(self, max_tier: Tier = Tier.ACT_MONEY, approval_tiers=(Tier.ACT_MONEY,)):
        self.max_tier, self.approval_tiers = max_tier, tuple(approval_tiers)

    def check(self, tool: str, tier: Tier) -> None:
        if tier > self.max_tier:
            raise PermissionDenied(f"{tool} needs tier {tier.name}; session max is {self.max_tier.name}")

    def needs_approval(self, tier: Tier) -> bool:
        return tier in self.approval_tiers


def _digest(prev: str, body: dict) -> str:
    return hashlib.sha256((prev + json.dumps(body, sort_keys=True)).encode()).hexdigest()


class AuditLog:
    """Local hash chain, reloaded and checked on open. Not immutable or externally anchored.
    A complete rewrite with recomputed hashes cannot be detected without an external anchor.
    One writer per path is supported; production needs transactional/append-only storage.
    """

    def __init__(self, path: str | None = None):
        self.entries: list[dict] = []
        self.path = path
        if path:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.exists():
                try:
                    self.entries = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
                except (ValueError, OSError) as exc:
                    raise ValueError("invalid persisted audit log") from exc
                if not self.verify():
                    raise ValueError("persisted audit chain failed verification")
            else:
                p.touch()

    def record(self, actor: str, action: str, detail: dict | None = None) -> dict:
        if not self.verify():
            raise ValueError("audit log integrity check failed before append")
        prev = self.entries[-1]["hash"] if self.entries else "GENESIS"
        safe = json.loads(mask_pii(json.dumps(detail or {}, default=str)))
        body = {"i": len(self.entries), "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "actor": actor, "action": action, "detail": safe, "prev": prev}
        entry = {**body, "hash": _digest(prev, body)}
        self.entries.append(entry)
        if self.path:
            with open(self.path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        return entry

    def verify(self) -> bool:
        try:
            if self.path:
                disk = [json.loads(line) for line in Path(self.path).read_text().splitlines() if line.strip()]
                if disk != self.entries:
                    return False
            prev = "GENESIS"
            for i, e in enumerate(self.entries):
                if not isinstance(e, dict):
                    return False
                body = {k: v for k, v in e.items() if k != "hash"}
                if body["i"] != i or body["prev"] != prev or _digest(prev, body) != e["hash"]:
                    return False
                prev = e["hash"]
            return True
        except (OSError, ValueError, KeyError, TypeError):
            return False
