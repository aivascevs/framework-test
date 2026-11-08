# Plan: SPEC-001 Refund total per customer

Specification: [spec.md](spec.md)

## Tasks

| # | Task | Files | Satisfies | How it is verified |
|---|---|---|---|---|
| 1 | Add `refunded_total(email)` with a parameterised `SUM` query | `sample-app/orders/store.py` | AC1, AC2, AC3, SEC1 | Tests in task 2. Semgrep rule `python-sql-built-from-strings`. |
| 2 | Add tests for a customer with refunds, without refunds and with mixed orders. Check that logs do not contain the e-mail. | `sample-app/tests/test_store.py` | AC1–AC3, DATA1 | `pytest` in CI |

## New dependencies

| Package | Version | Licence | Why |
|---|---|---|---|
| none | | | |

## Risks and stop conditions

- Stop and ask if the task needs a schema change.
- Stop if a check fails three times on the same finding.

## Plan approval

| Approved by | Date | Note |
|---|---|---|
| change-author | 2026-10-26 | Reviewed before the agent started |
