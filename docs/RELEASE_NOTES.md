# Release notes · 19 October 2026

Preserves the original offline Python prototype and its seeded synthetic dataset. Changes are scoped to safer demonstration behavior and reproducibility.

- Recommend only full-gap, affordable offers; safely refuse when none exists.
- Select the recommendation explicitly instead of blindly using the first visible product.
- Split application and disbursement into independent, mandatory approval gates.
- Generic application requests do not automatically disburse.
- Correct the metric name to simple annualized total cost, not effective APR/IRR.
- Reopen and verify persisted audit chains; detect file changes, malformed chains and stale writers.
- Validate finite/nonnegative requests; reject nonfinite ingestion amounts and negative sandbox applications.
- Floor repayment capacity at zero for loss-making businesses, producing refusal rather than a crash.
- Add 40 release-safety regressions; 64 tests total pass.
- Add eight-stage actual execution evidence, a captioned 2:40 MP4, and an optional localhost visual wrapper.

## Verification boundaries

Python 3.12 runtime used for this release. A GitHub workflow is included for Python 3.10/3.12, but remote CI was not run because no repository was published. HTTP API workflows and JavaScript parsing pass; browser-rendering/click QA was blocked by execution sandbox process restrictions. Video presents actual captured CLI outputs in a readable console layout and does not claim browser footage or voice narration.
