# Plan: <SPEC-NNN title>

The change author or the agent writes this plan. A human reviews the plan **before** the agent changes files (A8). Keep each task small.

Specification: [spec.md](spec.md)

## Tasks

| # | Increment | Task | Files | Satisfies | How it is verified | Est. lines |
|---|---|---|---|---|---|---|
| 1 | INC-1 | <task> | <paths> | AC1, SEC1 | <test name or check> | <~N> |
| 2 | INC-1 | <task> | <paths> | AC2 | <test name or check> | <~N> |

## Size (C9)

| Increment | Estimated changed lines | Files | Budget for the risk class | Fits |
|---|---|---|---|---|
| INC-1 | <~N> | <n> | <from policy-config/review-budget.yaml> | <yes / no: split> |

## New dependencies

| Package | Version | Licence | Why |
|---|---|---|---|
| <none> | | | |

## Risks and stop conditions

- Stop and ask the change author if a task needs a file, a command or a network host that the specification does not permit.
- Stop if a check fails three times on the same finding.

## Plan approval

| Approved by | Date | Note |
|---|---|---|
| | | |
