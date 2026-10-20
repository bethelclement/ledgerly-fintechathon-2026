# Ledgerly · SME Finance Copilot

Working offline MVP for **FinTechathon 2026, International Track, Topic E**.
Ledgerly turns synthetic SME transaction records into an explained cash-flow passport, a 13-week scenario forecast, an affordability-filtered illustrative financing comparison and a privacy-minimal lender pack. Applications and disbursements are separate, explicitly approved **sandbox** actions.

## Run in under a minute

Python 3.10+; the engine, CLI and local web wrapper use the standard library only. No API keys, accounts or network lender access are required.

```sh
python3 -m unittest discover -s tests -v   # 64 tests
python3 run_demo.py                       # real eight-stage CLI demo and evidence
python3 demo_server.py                    # optional localhost visual wrapper
```

Open http://127.0.0.1:8765 for the optional wrapper. Keep it on localhost; it has no production authentication and is not a deployable financial service.

## What is verified

- 64 unit/regression tests passed: 24 original + 40 release-safety regressions.
- 2,352 synthetic transaction records loaded; one instruction-like memo neutralized.
- Score 83.2/100; downside buffer gap ₦873,239, rounded to a ₦880,000 request.
- Illustrative MFB option: 24 weeks, ₦139,446 total cost, ₦42,477 weekly average payment.
- No approval: no application, no disbursement, balance ₦650,000.
- Application-only approval: simulated application approved; disbursement paused, balance unchanged.
- Separate disbursement approval: sandbox balance ₦1,530,000. Repeat is idempotent in-session.
- Stress fixture with expenses +60%: zero repayment capacity; no application or disbursement.
- Local audit reload validates; altered entries and malformed logs fail validation.
- Optional wrapper HTTP workflows and JavaScript syntax checked. Browser visual/click QA was blocked by the build sandbox and is not claimed.

The captured, captioned walkthrough is `demo/Ledgerly_Demo_2m40s.mp4` in the full release. It presents genuine CLI execution output, reformatted for readability; it is not a browser screen recording and has no voiceover. The source-only ZIP may omit the MP4, which is supplied separately.

## Important distinctions

This is an **offline, rule-planned prototype**, not a live LLM agent. An optional `llm_planner` callback is available and guarded, but no live model was integrated or tested. Catalogue terms, approvals and money are simulated. No real lender API, underwriting calibration, KYC or authenticated owner identity is implemented.

The displayed rate is **simple annualized total cost**, calculated as total cost ÷ principal × 52 ÷ term in weeks. It is not amortizing APR, IRR or a regulatory disclosure. Weekly payments are simplified averages. Affordability is a historical-cash-flow heuristic, not a lender decision.

A full-gap affordable offer is the only one eligible for automatic recommendation and pack preparation. Partial or unaffordable products remain visible for comparison and are never silently selected. Even an approving callback cannot bypass that selection rule.

## Files

- `ledgerly/`: ingestion, analysis, forecast, scoring, financing, guarded agent, audit and sandbox
- `run_demo.py`: eight-stage actual-execution demonstration
- `demo_server.py`, `web/index.html`: optional localhost interface using the same engine
- `tests/`: 64 tests
- `data/`: seeded synthetic dataset and generator
- `evidence/latest_run.txt`: name of the latest generated run folder
- `evidence/run_*/`: reports, stage reports, sandbox operations and audit JSONL
- `verification/`: captured test/CLI/API logs and video validation
- `docs/`: technical, security, local deployment and reproducibility notes
- `make_demo_video.py`: renders saved real CLI output as the captioned walkthrough

## Audit and safety limits

Local audit entries are persisted, reloaded and checked before append. This is a single-writer hash chain, not immutable storage; a complete rewrite with recomputed hashes has no external anchor to detect it. Sandbox applications, balances and idempotency are process-local. Restart-safe transactions, authenticated payload-bound approvals and secure production storage remain future work.

## Source publishing

Project repository: https://github.com/bethelclement/ledgerly-fintechathon-2026. This is source for an offline demonstration, not a hosted financial service. See `docs/LOCAL_DEPLOYMENT.md` for local startup and review requirements.
