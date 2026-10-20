# Ledgerly technical documentation

Final prototype release  •  Topic E SME Finance Copilot  •  19 October 2026

Ledgerly is a local Python finance-copilot prototype for a synthetic Nigerian trading business. It turns transaction records into an explainable passport, cash-flow scenarios and financing comparisons, then demonstrates owner-controlled application and disbursement in a sandbox. The release is a reproducible demonstration, not a live financial product.

## Release scope and evidence

The verified core is the command-line application. The final suite contains 64 passing tests: 24 existing tests and 40 release-safety regressions. A localhost visual wrapper is included as optional source, but browser end-to-end quality assurance was not completed. The demo video is a captioned capture of the actual command-line workflow.

The baseline planner is deterministic and keyword-based. An optional externally supplied LLM callback is present; no live model, provider connection, model benchmark or natural-language accuracy claim is part of this release. The core uses the Python standard library and needs no API key.

## System architecture

| Layer | Implementation and responsibility |
| --- | --- |
| Input and validation | ingest.py parses the CSV, rejects invalid dates and non-finite amounts, categorizes records and screens memo text. |
| Financial analysis | analysis.py aggregates monthly and weekly records. passport.py builds the heuristic. forecast.py projects cash under fixed scenarios. |
| Financing comparison | financing.py evaluates a fixed illustrative catalogue, exposes cost and repayment load, and selects only a full-gap affordable offer. |
| Orchestration | agent.py resolves a plan through a tool registry, dependencies, permission checks and approval callbacks. |
| Controls and evidence | security.py handles purpose checks, masking and hash-chained local logs. sandbox.py simulates notifications, applications and disbursements. |
| Interfaces | run_demo.py runs the core example. demo_server.py and web/index.html provide an optional localhost-only visual wrapper. |

## Data and authority boundaries

Records enter a local process. Analytical tools produce local results. A pack is a prepared disclosure object, not evidence of transmission to a lender. The only action adapter is SandboxEnv: it records simulated operations and modifies an in-memory balance. There is no bank, payments, messaging or lender network integration. A planner proposes registered tools; it does not receive an arbitrary command-execution tool.

## Input contract and preprocessing

The CSV columns are date, amount, description, channel and counterparty. Dates use ISO format; positive amounts are treated as sales and negative amounts as outflows. Expense categories are keyword rules for loan repayment, owner draw, supplier, rent, wages and transport, with a fallback category. The demo is single-currency NGN; it does not perform foreign-exchange conversion.

The fixed example contains 2,352 synthetic rows from 29 September 2025 to 26 September 2026. Memos matching an instruction-like pattern are redacted and counted. Email addresses, common Nigerian phone patterns and 10- or 11-digit identifiers are masked in screened text. Counterparty strings remain available inside the analysis process; masking is not comprehensive anonymization.

## Financial metric definitions

- Monthly revenue is the sum of positive entries. Operating cash is revenue less operating outflows; loan repayments and owner draws are kept separate.

- Months are retained when the overall date span covers at least 80% of their calendar days. This is a span-based completeness proxy, not a reconciliation against bank records.

- Weekly repayment capacity is max(0, 50% × average monthly operating cash ÷ 4.345). It is a conservative-looking heuristic, not validated affordability or a stressed debt-service schedule.

- Customer concentration uses the largest named customer’s share of named sales, excluding walk-in records. Cash share uses sales tagged as cash. Missing names can change these measures.

## Seven factor cash flow passport

| Factor | Weight | Normalized contribution before clamping to 0 through 1 |
| --- | --- | --- |
| Record history | 10 | Accepted months ÷ 12 |
| Revenue stability | 20 | 1 − monthly revenue coefficient of variation ÷ 0.6 |
| Operating margin | 20 | Operating margin ÷ 0.20 |
| Sales trend | 10 | 0.5 + 2.5 × growth of the last 3 months versus the preceding 3 |
| Customer spread | 10 | 1 − (largest named-customer share − 0.10) ÷ 0.30 |
| Debt-service coverage | 20 | (Operating cash ÷ recorded loan payments − 1) ÷ 2; 0.7 when no debt service is recorded |
| Repayment record | 10 | Months with a repayment ÷ months since first repayment; 0.5 when none is recorded |

Weighted contributions are rounded and summed on a 0–100 scale. Grades are A at 75, B at 60, C at 45 and D below 45. The two largest weighted shortfalls produce improvement tips. Demographic fields do not enter this scoring function. The heuristic is not calibrated to defaults, lender acceptance or repayment performance; recorded repayments do not establish on-time payment.

## Forecast methodology

Weekly aggregation drops a partial first week and a final week ending before Saturday. For at least 52 weeks of observations, the model uses the same weeks one year earlier with a three-week centered average. With at least 60 weeks, recent eight-week revenue adjusts the level, bounded between 0.8 and 1.25. For shorter histories, it uses the last eight weeks after adjustment for monthly factors; month factors are shrunk 30% toward 1.

The horizon is 13 weeks. Base inflows use the baseline; downside inflows are multiplied by 0.8; upside inflows by 1.1. Outflows are unchanged in all three. Each closing balance equals the previous balance plus inflows minus outflows. The safety buffer is two times average projected weekly outflow. The buffer gap is max(0, safety buffer − minimum projected closing balance).

## Reproducible synthetic example

| Measure | Example output |
| --- | --- |
| Opening cash | NGN 650,000 |
| Passport | 83.2 / 100, grade A, from the heuristic only |
| Average monthly revenue | NGN 2,828,983 |
| Weekly repayment capacity | NGN 76,739 |
| Base minimum closing cash | NGN 686,717 in the week of 5 October 2026 |
| Downside minimum closing cash | NGN 357,653 in the week of 30 November 2026 |
| Upside minimum closing cash | NGN 809,848 in the week of 5 October 2026 |
| Two-week target buffer | NGN 1,230,892 |
| Downside buffer shortfall | NGN 873,239, rounded up to a request of NGN 880,000 |
| Negative cash week | None in any of the three example scenarios |

Values above are rounded for display. The synthetic example has a buffer shortfall, not a forecast cash insolvency. Restoring a preferred buffer is not itself proof that borrowing is necessary or prudent. The same forecasting outputs should be considered alongside non-borrowing options such as smaller purchases, supplier timing or retained cash.

## Forecast limitations

The downside is a fixed sensitivity, not a calibrated confidence interval. The model does not estimate probabilities, forecast accuracy or causal effects. Sparse history, missing weeks, structural changes, unreliable categories and one-year seasonality can produce misleading projections. The plotted cash path does not incorporate a proposed loan’s full repayment schedule or funding delay; production suitability requires that additional analysis.

## Illustrative financing catalogue

All products and terms are synthetic examples. They are not current offers, quotes, endorsements or commitments from financial institutions. The internal nominal-rate field is used for simple interest arithmetic; the reported annualized cost is not an effective APR or IRR.

| Product | Score | Rate and fee | Weeks | Maximum principal |
| --- | --- | --- | --- | --- |
| Bank working capital | 70 | 28% yearly + 1% | 16 | 1.0 × monthly revenue; collateral required |
| Fintech cash flow | 55 | 36% yearly + 2% | 12 | 0.6 × monthly revenue |
| Microfinance group | 40 | 30% yearly + 2% | 24 | 0.5 × monthly revenue |
| Supplier credit | 45 | 0% yearly + 2% | 2.9 | 0.5 × monthly revenue |
| Mobile money overdraft | 35 | 60% yearly + 3% | 4 | 0.1 × monthly revenue, capped at NGN 150,000 |

## Cost and selection rules

- Principal need is rounded up to NGN 10,000. An explicit zero request stays zero. Non-finite or negative financing inputs are rejected.

- Simple interest = principal × nominal annual rate × term weeks ÷ 52. Fee = principal × fee percentage. Total cost = interest + fee.

- Average weekly payment = (principal + total cost) ÷ term weeks. Affordability is tested on the unrounded value against the heuristic weekly capacity.

- Simple annualized cost rate = total cost ÷ principal × 52 ÷ term weeks. This ignores detailed payment timing and compounding and must not be relabeled APR.

- A recommendation must pass eligibility, fit the repayment-capacity heuristic and cover the entire rounded request. Partial or unaffordable options can be shown for comparison but cannot populate the executable request.

- If no suitable option exists, recommended_offer is empty and application and disbursement are skipped. The narrative explains the refusal. Among qualifying options, selection uses annualized cost, then total cost and product ID as tie-breakers.

## Selected example and unresolved judgment

The synthetic baseline selects the microfinance group product: NGN 880,000 over 24 weeks, NGN 139,446 total cost, about NGN 42,477 per week and 34.3% simple annualized cost. This meets the coded heuristic, not a validated determination that the business should borrow. Existing debt, owner draws, a stressed post-loan cash path and funding timing need fuller treatment before any real recommendation.

## Agent execution and approvals

The registry has eight tools: forecast, passport, alerts, match, pack, notify, submit and disburse. Dependency resolution adds prerequisites, removes duplicates and drops unknown tool names. The policy checks each tool’s tier before execution. Consent to credit_assessment is required for the passport; consent to share_with_lender is required to prepare the pack.

Submit and disburse are separate ACT_MONEY tools and each requires an approval callback when an executable offer exists. Approval cannot be disabled by passing an empty configurable approval-tier tuple. A generic apply goal does not plan disbursement. An explicit disbursement request requires an approved sandbox application and a separate approval step. Declining or omitting approval pauses the run with pending_approval.

Sandbox idempotency keys prevent repeated actions within the same environment instance. Approval callbacks and optional UI buttons are demonstration controls, not authenticated legal consent. The local UI remembers approved tool names within a demo session; it does not cryptographically bind consent to an immutable payload, identity or expiry.

## Reproduce and inspect

Use Python 3.10 or later from the source root. No model credentials or third-party Python dependencies are needed for the core.

python3 -m unittest discover -s tests -v

python3 run_demo.py

python3 demo_server.py

The first command runs 64 tests. The second writes final demonstration reports and logs as described in README. The optional server binds to http://127.0.0.1:8765; use only synthetic data locally. Do not expose it as a production service. Browser end-to-end verification remains outstanding.

## Evidence map

| Evidence | How to review it |
| --- | --- |
| verification/tests_final.txt | Confirm the 64-test passing result and test names against the supplied source. |
| tests/test_ledgerly.py | Existing behavioral tests for ingestion, analysis, forecast, matching and permissions. |
| tests/test_release_safety.py | 40 safety regressions covering recommendation refusal, separate approvals, invalid inputs, replay and audit integrity. |
| evidence/ and release video | Inspect the final reports and JSONL operations; confirm every action is marked sandbox. The video shows actual CLI execution with captions. |
| README and deployment guide | Follow the release-specific commands and final evidence paths; use the supplied final source version. |

Tests establish the listed behavior on synthetic fixtures. They do not establish regulatory compliance, production security, predictive accuracy, lending fairness, legal consent or a successful real-world deployment. Source paths in this report refer to the final release; earlier recovered archives and screenshots are superseded.
