# Local deployment and reproduction

## Engine and CLI

1. Extract the source ZIP and enter the `ledgerly` directory.
2. Install Python 3.10 or newer from the official Python distribution if needed.
3. Run `python -m unittest discover -s tests -v`.
4. Run `python run_demo.py`.
5. Read `evidence/latest_run.txt`, then inspect that run folder's JSON reports and logs.

Each run gets a fresh timestamped evidence folder. Earlier audit histories are not silently truncated. `AuditLog(path)` reloads an existing chain; the sandbox's money state itself remains process-local.

## Optional browser wrapper

Run `python demo_server.py`, then open http://127.0.0.1:8765 on the same computer. This is a local synthetic demo, not a publicly deployed application. It has explicit demo buttons for application and disbursement approvals. The HTTP workflow was checked; browser-rendering and click-based QA were blocked by the build sandbox. Do not treat this wrapper as authenticated owner approval.

The server binds to loopback only, accepts only fixed synthetic actions and rejects cross-origin action requests. It is single-session and has no production login, HTTPS termination, rate limits, user isolation, CSRF-token system or real consent record.

## Rebuild the video (optional Linux tooling)

The engine does not need video dependencies. To rebuild the walkthrough on a system with `ffmpeg`, Pillow and DejaVu fonts:

```sh
python run_demo.py
python make_demo_video.py
```

The video renderer consumes actual `evidence/demo_steps.json` from the executed CLI. It does not invent outcomes. It emits a silent, captioned 160-second MP4, an SRT caption file and a transcript. Rendered console formatting is not a screen recording.

## Before any public/real-money release

Complete authenticated, payload-bound approval and consent flows; durable transactional/idempotency storage; externally anchored audit logs; account and data isolation; full browser QA; tested ingestion adapters; legal/compliance review; KYC and lender contracts; lender-term and repayment-schedule validation; calibrated underwriting and fairness evaluation. Keep real financial actions disabled until those controls exist.

No external deployment or GitHub publication was performed for this release.
