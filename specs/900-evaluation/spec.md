---
# Evaluation specification. Used only by the evaluation scenarios on a test repository
# (evaluation/host_scenarios.sh). It permits the sample application without its auth
# module, so that a scenario fails only on the check that it tests.
id: SPEC-900
title: "Evaluation scenarios on the sample application"
owner: "evaluation-operator"
risk_class: Elevated
risk_confirmed_by: "evaluation-lead"
data_class: internal
ai_use: edit
ai_tool: claude-code
capability_profile: P1
status: approved
---

# Evaluation scenarios on the sample application

## 1. Purpose

Run the evaluation scenarios of `evaluation/protocol.md` as pull requests on a test repository. Each scenario applies one fixture.

## 2. Scope

- In scope: fixture changes under `sample-app/`, except `sample-app/auth/`.
- Out of scope: any merge. Close each scenario pull request after you record the result.

## 3. Affected components

- `sample-app/orders/`, `sample-app/tests/`, `sample-app/requirements.txt`, `sample-app/README.md`

## 4. Acceptance criteria

- **AC1** — WHEN a scenario pull request is opened, the CI checks SHALL report the result that `evaluation/protocol.md` expects.
- **AC2** — WHEN the result is recorded, the operator SHALL close the pull request without a merge.

## 5. Security and privacy requirements

- **SEC1** — Fixtures SHALL contain only synthetic secrets and invented personal data.
- **DATA1** — The scenarios SHALL NOT use real credentials, real personal data or production endpoints.

## 6. Dependency and licence requirements

- **LIC1** — New dependencies SHALL have a licence in `policy-config/allowed-licenses.txt`, or an approved exception.
- New dependencies expected: only the manifest fixtures of S08 and S09. Nobody installs them.

## 7. Permitted capabilities

| Item | Value |
|---|---|
| Capability profile | P1 Edit |
| Files the agent may change | `sample-app/orders/**`, `sample-app/tests/**`, `sample-app/requirements.txt`, `sample-app/README.md` |
| Commands the agent may run | none |
| Network access | none |
| Generated files | none |
| External tools or MCP servers | none |

## 8. Increments (C9)

Each scenario is one pull request. Nobody merges it.

| ID | Reviewable result | Files | Estimated changed lines | Depends on | Status |
|---|---|---|---|---|---|
| INC-1 | One scenario fixture | `sample-app/orders/**`, `sample-app/tests/**`, `sample-app/requirements.txt`, `sample-app/README.md` | ~50 | — | planned |

## 9. Open questions

- None

## 10. Approval

| Step | Name | Date |
|---|---|---|
| Risk class approved by the technical lead (Elevated and above) | evaluation-lead | 2026-11-07 |
| Specification approved | evaluation-operator | 2026-11-07 |
