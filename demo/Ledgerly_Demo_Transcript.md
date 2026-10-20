# Ledgerly: actual offline execution walkthrough

Format: captioned MP4, no voiceover. Output captured from `python run_demo.py`; terminal layout is reformatted for readability. Not a browser recording.

## 01  INGEST & PROTECT
A synthetic Lagos trader starts with 2,352 records. One poisoned memo is treated as data and neutralized.

```text
LEDGERLY | SME FINANCE COPILOT
Mode: offline / synthetic / sandbox only
Records loaded: 2,352 | Rejected: 0
Instruction-like memos neutralized: 1
Data window: 2025-09-29 to 2026-09-26
Planner: deterministic rules; no live LLM calls
External bank calls: 0 | Real money moved: NGN 0
```

## 02  EXPLAIN THE RISK
The downside case stays positive but falls below the two-week buffer. The score is an explained heuristic, not a lender credit rating.

```text
Cash-flow passport: 83.2/100 | Grade A
Forecast: 13 weeks | Base / sales -20% / sales +10%
Downside minimum cash: NGN 357,653
Minimum week: 2026-11-30
Two-week safety buffer: NGN 1,230,892
Buffer gap: NGN 873,239 -> request NGN 880,000
Weekly repayment capacity: NGN 76,739
A buffer shortfall, not a forecast of insolvency.
```

## 03  COMPARE RESPONSIBLY
Only an affordable offer covering the full gap can be selected. The lower-cost, faster products are not automatically safer.

```text
PRODUCT                   WEEKLY    FULL GAP   AFFORDABLE
MFB-GRP                   42,477    yes        yes
MM-OD                     40,356    no         yes
SUP-NET30                309,517    yes        no
FIN-CF                    80,892    yes        no

Recommended: Microfinance group loan
NGN 880,000 / 24 weeks | Total cost NGN 139,446
Simple annualized cost: 34.3% (NOT APR or IRR)
Catalogue is illustrative. No real lender quotes.
```

## 04  FIRST APPROVAL GATE
Consent allows the local lender pack. Application approval is still required; no application or money movement has happened.

```text
Status: pending_approval | Pending tool: submit
Lender pack: business summary + factors + forecast + offer
Excluded: raw transactions, customer identities, account numbers
Sandbox applications: 0 | Disbursements: 0
Sandbox balance: NGN 650,000
Waiting for explicit application approval.
```

## 05  APPLICATION IS NOT DISBURSEMENT
Approving the application does not approve disbursement. The engine stops again, and the balance is still NGN 650,000.

```text
Application: APPROVED (simulated lender)
Status: pending_approval | Pending tool: disburse
Sandbox balance: NGN 650,000 (unchanged)
Disbursements: 0
A separate owner decision is required to disburse.
```

## 06  APPROVE ONCE, EXECUTE ONCE
After the second explicit approval, the sandbox balance rises. Repeating the approved workflow does not duplicate the transfer in this session.

```text
Disbursement: DISBURSED | Sandbox only
Sandbox balance: NGN 1,530,000
Repeated run balance: NGN 1,530,000
Total application operations: 1
Total disbursement operations: 1
Replay flagged: True
Idempotency is in-process; restart-safe money state is not implemented.
```

## 07  THE SAFE ANSWER CAN BE NO
With higher expenses, repayment capacity becomes zero. The engine refuses the financing path, even when the demo approval callback says yes.

```text
Weekly repayment capacity: NGN 0
Recommended offer: None
Application: SKIPPED
Disbursement: SKIPPED
Sandbox balance: NGN 650,000 (unchanged)
No affordable full-gap offer. Application and disbursement refused.
Even an approving callback cannot override this affordability gate.
```

## 08  VERIFY THE EVIDENCE
The evidence is reproducible: code, tests, execution logs and audit records. This is a working offline prototype, with production gaps clearly stated.

```text
Persisted audit reload: True
Audit entries: 47
Tampered copy verifies: False
Local hash chain, not immutable or externally anchored.
Full suite: 64 passing tests (24 original + 40 regressions).
Production gaps: authenticated approvals, calibrated risk,
live lender APIs, durable transactions, external audit anchoring.
Run locally: python demo_server.py (optional visual wrapper)
```
