# Ledgerly — Security Self-Assessment

**FinTechathon 2026 | International Track | Topic E: SME Finance Copilot**  
**Release:** 20 October 2026  
**Assessment basis:** Source review and 64 local unit/regression tests.

## System boundary

Ledgerly processes synthetic trading records on a local Python runtime. The baseline planner is deterministic; the optional model callback is not connected to a live model. Lender offers, notifications, applications, balances and disbursements are simulated. There are no banking integrations, production credentials or real customer records.

## Implemented controls

| Area | Control and evidence |
| --- | --- |
| Tool permissions | Registered actions are grouped as READ, PREPARE, ACT_LOW and ACT_MONEY. The agent checks the session's permitted tier. |
| Data-use purpose | Credit assessment and lender-pack preparation require their respective purpose grants. |
| Consequential actions | Simulated application and disbursement require separate affirmative approval callbacks. Declined or missing approval pauses execution. |
| Financing selection | Only an eligible offer that covers the full requested amount and passes the coded repayment-capacity check may be selected. If none qualifies, no action is attempted. |
| Data minimization | The prepared lender pack excludes raw transaction rows and direct customer identifiers. Local memo screening masks selected phone numbers, emails and numeric identifiers. |
| Audit records | Indexed SHA-256 hash-chained JSONL records are verified before append; malformed or inconsistent logs are rejected. |
| Sandbox | Simulated principal is capped at NGN 5,000,000. Duplicate disbursement is blocked within the same in-memory sandbox instance. |
| Web wrapper | Optional UI binds to 127.0.0.1:8765 and checks allowed action paths and supplied Origin headers. |

## Material risks and required work

| Priority | Current limitation | Required before live use |
| --- | --- | --- |
| Critical | No authenticated owner identity or payload-bound legal consent. | Verified sessions; approval bound to transaction terms, scope and expiry; revocation and replay protection. |
| Critical | Banking and lender adapters have not been implemented or tested. | Isolated credentials; integration and recipient validation; transaction limits; reconciliation and operational review. |
| High | Local files and logs are not encrypted, access-controlled or subject to a retention process. | Secure storage, access management, retention and deletion controls. |
| High | Forecasts, affordability checks and the seven-factor passport are unvalidated heuristics. | Accuracy testing on consented data, stressed repayment schedules, financial review and monitoring. |
| High | Identifier masking and hostile-input screening are incomplete. | Input constraints, allowlisted disclosures and adversarial tests. |
| High | Audit integrity depends on the local operator; deduplication does not survive a restart. | Independent audit anchoring, durable idempotency and transaction-safe persistence. |
| High | No protected-group outcomes have been evaluated. | Fairness monitoring and documented assessment with appropriate governance. |
| Medium | The optional UI and model callback are not production hardened. | Authentication, browser testing, model-output validation, error handling and security testing. |

## Verification

Run from the repository root with Python 3.10 or later:

```bash
python3 -m unittest discover -s tests -v
python3 run_demo.py
```

The release test suite contains 64 passing tests (24 original cases and 40 safety regressions). Coverage includes refusal of unaffordable or partial financing, separate application/disbursement approvals, zero and invalid inputs, in-session replay and audit-log integrity. The optional localhost UI has not completed end-to-end browser testing.

## Assessment status

This is a team security self-assessment, not an independent penetration test or compliance certification. The release is appropriate for a synthetic, offline competition demonstration only. It must not be used for real financial records, lending decisions or money movement without the controls above.
