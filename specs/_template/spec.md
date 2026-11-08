---
# Change specification (C2). Copy this folder to specs/NNN-short-name/.
# CI reads the fields between the --- lines. Keep the field names.
id: SPEC-NNN
title: "<short title>"
owner: "<name of the accountable change author>"
risk_class: Routine            # Routine | Elevated | High impact | Restricted
risk_confirmed_by: ""          # technical lead. Required for Elevated and above.
data_class: internal           # public | internal | confidential | personal | secret
ai_use: edit                   # none | suggest | edit | execute | connected
ai_tool: claude-code           # an id from governance/approved-tools.yaml, or none
capability_profile: P1         # P0 | P1 | P2 | P3 (see governance/risk-and-capability.md)
status: draft                  # draft | approved
---

# <Title>

## 1. Purpose

<What must change, and why. One or two sentences.>

## 2. Scope

- In scope: <...>
- Out of scope: <...>

## 3. Affected components

- <path or component>

## 4. Acceptance criteria

<Each criterion is testable. Use SHALL for a requirement and SHALL NOT for a prohibition.>

- **AC1** — WHEN <condition>, the system SHALL <behaviour>.
- **AC2** — <...>

## 5. Security and privacy requirements

<Write "None" only for a Routine change with no security effect.>

- **SEC1** — <for example: Input to the new endpoint SHALL be validated against the schema.>
- **DATA1** — <for example: The service SHALL NOT write e-mail addresses to logs.>

## 6. Dependency and licence requirements

- **LIC1** — New dependencies SHALL have a licence in `policy-config/allowed-licenses.txt`, or an approved exception.
- New dependencies expected: <none, or package@version and why>

## 7. Permitted capabilities

| Item | Value |
|---|---|
| Capability profile | <P0–P3> |
| Files the agent may change | <paths> |
| Commands the agent may run | <for example: `pytest`, `python -m app`> |
| Network access | <none, or approved package sources only> |
| Generated files | none <!-- or: `path` — produced by `command`. CI does not count their lines (C9). --> |
| External tools or MCP servers | none |

## 8. Increments (C9)

<One increment is one pull request that a reviewer can read in full. The budget for each risk class is in `policy-config/review-budget.yaml` (for example 400 changed lines for Elevated, 200 for High impact). If the estimate for the whole change is above the budget, split the change. The `change-splitter` skill proposes the split. Put `Increment: INC-n` in each pull request.>

| ID | Reviewable result | Files | Estimated changed lines | Depends on | Status |
|---|---|---|---|---|---|
| INC-1 | <one behaviour, with its tests> | `<paths>` | <~N> | — | planned |

## 9. Open questions

- <question, or "None">

## 10. Approval

| Step | Name | Date |
|---|---|---|
| Risk class approved by the technical lead (Elevated and above) | | |
| Specification approved | | |
