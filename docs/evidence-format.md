# Evidence Format (C7)

Each pull request gets one evidence summary. The CI job `Evidence summary` writes it as the artifact `evidence-summary` and adds it to the job summary of the run.

The evidence summary is not an audit trail. It links the change, the declared metadata and the check results at one commit. The pull request history and the CI logs on the source-control host hold the other records.

## Fields

| Field | Source | Note |
|---|---|---|
| Repository, pull request, commit | CI environment | The commit is the head of the pull request |
| Specification | PR metadata | Path to the spec file |
| Risk class, data class, AI use, AI tool, capability profile | Specification front matter (read by CI) | Declared by the change author. The light path (`Specification: none`) takes them from the PR body. |
| Exception | PR metadata | Link to the exception record, or `none` |
| Minimum risk class for the changed paths | `check_guardrails.py` | From `policy-config/risk-paths.yaml` |
| Size and review order (C9) | `check_guardrails.py` | Changed lines and files against the budget. Files ranked by path risk, then size. |
| Requires human review | `check_guardrails.py` | Removed tests, suppression markers, governance-file changes, findings accepted by an exception |
| Result of each check | CI jobs | `success`, `failure`, `skipped` or `cancelled` |
| Tool versions | Workflow environment | Pinned in `.github/workflows/governance.yml` |
| Human approval | Not in the summary | The host records approvals. Read them in the pull request. |
| Generated at | CI clock | UTC |

## What the evidence summary does not contain

- Raw prompts or model output. See principle 5 in [governance/policy.md](../governance/policy.md).
- Source code, secrets or personal data.
- A claim about which lines a model wrote.

## Retention

The source-control host keeps the artifact for its configured retention period (GitHub default: 90 days). If you need longer retention, copy the summary to a store that your organisation controls, and record that decision in the policy.
