# Reviewer Checklist (C6)

Use this checklist for every pull request with AI use other than `none`. A passed CI run does not replace this review. A passed scan does not prove that the change is correct or secure.

## 1. Before you read the code

- [ ] The pull request links a specification, and the specification is `approved`.
- [ ] The risk class fits the change. If you think the class is too low, ask for a new classification.
- [ ] You did not prepare this change yourself, with or without an agent.
- [ ] For a High impact change: you have the expertise for the affected area, or a specialist reviews too.
- [ ] The AI tool and mode are in `governance/approved-tools.yaml`.
- [ ] The pull request is inside the change budget (C9), or an approved exception covers it. It names its increment.

## 2. While you read the code

Read the files in the suggested review order in the evidence summary (highest risk first). If the change is too large to read in full, request a split. Do not approve what you did not read.

- [ ] Every acceptance criterion (AC) has an implementation and a test.
- [ ] Every security, data and licence requirement (SEC, DATA, LIC) holds in every new code path.
- [ ] Tests check the required behaviour. They do not only repeat the implementation.
- [ ] No new dependency is present that the specification does not list.
- [ ] No code looks copied from an external source without its licence notice.
- [ ] No secrets, real personal data or production endpoints are present, including in tests and fixtures.
- [ ] No change weakens a check: no new suppression, no lower threshold, no removed test.
- [ ] Changes to `AGENTS.md`, `.claude/`, `.vscode/`, `.github/` or `governance/` have a reason in the specification.

## 3. After the checks

- [ ] All required checks passed, or an approved exception covers each failure.
- [ ] You read each item under "Requires human review" in the evidence summary (removed tests, suppression markers, governance-file changes) and agree with it.
- [ ] You read the open findings of the `reviewer` agent. They are input, not proof.
- [ ] Each finding that needs a human decision (licence, unclear code origin, disputed finding) has a recorded decision.
- [ ] You can explain the change in your own words.

## 4. Record your decision

Approve, or request changes, in the pull request. Add a comment for each decision on a licence, an exception or a disputed finding. The approval record shows that a review happened. It does not show how good the review was. Your accountability is real even when the record is short.
