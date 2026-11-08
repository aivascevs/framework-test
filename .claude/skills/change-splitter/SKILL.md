---
name: change-splitter
description: Split a change that is too large for one review into small increments, one pull request each (C9 reviewability gate). Use when the estimate for a plan or a specification is above the budget for its risk class. Also use when CI reports review-budget or new-file-size, when the working diff grows past the budget, or when the user invokes /change-splitter.
argument-hint: "<specification path>"
---

# Change Splitter

Principle 7: delegate only up to the reviewing capability. A reviewer must be able to read every line of a pull request. This skill keeps each pull request inside the budget in `policy-config/review-budget.yaml` by splitting the work into increments. **You propose the split. The change author approves it** as part of the specification (gate 1).

Mode: Advisory. CI checks the size of each pull request (`scripts/check_guardrails.py`, check `review-budget`).

## Step 1. Get the budget

1. Read `risk_class` in the specification front matter.
2. Read the budget for that class in `policy-config/review-budget.yaml`: `max_changed_lines`, `max_files` and `max_new_file_lines`.
3. Set the target for one increment to about **70 % of the budget**. Estimates are low more often than high.

## Step 2. Estimate the size

1. Take the plan tasks from the `planner` agent, or the acceptance criteria if no plan exists yet.
2. For each task, estimate the changed lines (added plus deleted) and the files. Count the tests too. Tests are part of the review.
3. Do not count files that `review-budget.yaml` excludes (lock files, snapshots, images). Do not count generated files that section 7 lists under "Generated files".
4. Add the totals. If the total is below the target, write one increment (`INC-1`) and stop.

## Step 3. Split

Apply these rules in order. Each rule makes the review easier, not only shorter.

1. **Mechanical first.** Put renames, moves, formatting and refactoring without a change in behaviour in their own increment. The reviewer can check them quickly. Never mix them with a change in behaviour.
2. **Dependencies alone.** Put a new or upgraded package in its own increment, after the `dependency-check` skill.
3. **Generated code alone.** Put generated files in their own increment. List them under "Generated files" in section 7 with the command that produces them. The reviewer checks the generator and its input.
4. **One behaviour per increment.** Each remaining increment delivers one testable result: one or more acceptance criteria with their tests. Keep a security requirement and its test in the same increment.
5. **High-risk code in a small increment.** Put changes to paths that `policy-config/risk-paths.yaml` marks as High impact in a separate, small increment, so the deep review is focused.
6. **Each increment can merge alone.** The build and the tests pass after each increment. If a user would see a half-finished feature, hide it behind a flag or keep it unreachable until the last increment. For a database change, add first and delete later (expand, then contract).
7. **Order by dependency.** An increment never depends on a later increment.
8. **Check each increment** against the target: lines, files and the largest new file.

If you need more than **six increments**, the change is too large for one specification. Propose separate specifications instead, and tell the user why.

Parts of the work can have very different risk, for example a UI text change and an authentication change. Then propose separate specifications. The low-risk part does not have to wait for the high-risk review.

## Step 4. Write the increments

1. Fill section 8 of the specification:

   ```markdown
   | ID | Reviewable result | Files | Estimated changed lines | Depends on | Status |
   |---|---|---|---|---|---|
   | INC-1 | Rename OrderRepo to OrderStore (no behaviour change) | `src/orders/*.py` | ~120 | — | planned |
   | INC-2 | Refund total, AC1–AC2, with tests | `src/orders/store.py`, `tests/test_store.py` | ~180 | INC-1 | planned |
   ```

2. List in each increment only files from section 7. CI limits the pull request of an increment to its files.
3. Keep `status: draft` in the front matter. The change author approves the split with the specification.

## Step 5. Hand over

Tell the user, in short sentences:

- the budget, the total estimate and the number of increments
- one line for each increment: what the reviewer will see
- that each increment is one pull request with the line `Increment: INC-n`
- that the next increment starts after the previous one is merged, or as a stacked branch on it

## During implementation

The `governed-change` skill checks the size of the working diff before the pull request:

```bash
python scripts/check_guardrails.py --spec specs/NNN-name/spec.md --increment INC-n --base main --worktree
```

If the check reports `review-budget` or `new-file-size`:

1. Stop adding code.
2. Find the last point where the build and tests pass and the change is complete for a reviewer.
3. Move the remaining tasks to a new increment in section 8. Tell the user: a change to the specification needs their approval.
4. Do not hide size: do not squeeze code onto fewer lines, do not move code into excluded or generated paths, and do not delete tests.

Only the risk owner can accept an over-budget pull request, with an exception record (`exception-drafter` skill).
