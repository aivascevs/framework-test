---
id: SPEC-001
title: "Refund total per customer"
owner: "change-author"
risk_class: Elevated
risk_confirmed_by: "technical-lead"
data_class: internal
ai_use: edit
ai_tool: claude-code
capability_profile: P1
status: approved
---

# Refund total per customer

## 1. Purpose

Support staff need the total refunded amount for one customer. Add a store method that returns this total.

## 2. Scope

- In scope: a new method in `sample-app/orders/store.py` and its tests.
- Out of scope: any API, user interface or schema change.

## 3. Affected components

- `sample-app/orders/store.py`
- `sample-app/tests/test_store.py`

## 4. Acceptance criteria

- **AC1** — WHEN a customer has refunded orders, `refunded_total(email)` SHALL return the sum of their amounts in cents.
- **AC2** — WHEN a customer has no refunded orders, `refunded_total(email)` SHALL return 0.
- **AC3** — `refunded_total(email)` SHALL NOT include orders that are not refunded.

## 5. Security and privacy requirements

- **SEC1** — The query SHALL use parameters. It SHALL NOT build SQL text from the e-mail value.
- **DATA1** — The method SHALL NOT write the e-mail address to logs.

## 6. Dependency and licence requirements

- **LIC1** — The change SHALL NOT add dependencies.
- New dependencies expected: none

## 7. Permitted capabilities

| Item | Value |
|---|---|
| Capability profile | P1 Edit |
| Files the agent may change | `sample-app/orders/store.py`, `sample-app/tests/test_store.py` |
| Commands the agent may run | none (the developer runs `pytest`) |
| Network access | none |
| Generated files | none |
| External tools or MCP servers | none |

## 8. Increments (C9)

The whole change fits the Elevated budget (400 changed lines), so it is one increment.

| ID | Reviewable result | Files | Estimated changed lines | Depends on | Status |
|---|---|---|---|---|---|
| INC-1 | Refund total with its tests | `sample-app/orders/store.py`, `sample-app/tests/test_store.py` | ~60 | — | done |

## 9. Open questions

- None

## 10. Approval

| Step | Name | Date |
|---|---|---|
| Risk class approved by the technical lead (Elevated and above) | technical-lead | 2026-10-26 |
| Specification approved | change-author | 2026-10-26 |
