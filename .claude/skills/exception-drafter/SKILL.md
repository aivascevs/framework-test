---
name: exception-drafter
description: Draft an exception record for a finding that a team decides to accept for a limited time. Examples: a licence outside the allowlist, a known advisory without a fix, a guardrail finding on a governance change. Use when the user invokes /exception-drafter or asks to accept a risk. The risk owner approves the draft.
argument-hint: "<finding and pull request link>"
---

# Exception Drafter

An exception accepts a residual risk for a limited scope and time. It does not remove the finding. This skill fills the template `governance/exception-template.md`. **The risk owner approves the exception, not you.** Leave the approval fields empty.

Mode: Manual. CI accepts the exception only while it has an expiry date in the future (`scripts/check_metadata.py`).

## Step 1. Collect the facts

1. Read the finding: the CI job output, the reviewer comment or the checker result.
2. Read the specification of the change and its risk class.
3. Ask the user, in one message, only for what you cannot find:
   - Why must the change continue now?
   - What reduces the risk (compensating measures)?
   - Who is the risk owner?
   - Until when (the expiry date)? Propose 90 days or less.

## Step 2. Draft the record

1. Find the next free number in `governance/exceptions/` (create the folder if it does not exist).
2. Copy `governance/exception-template.md` to `governance/exceptions/EXC-NNN-<short-name>.md`.
3. Fill every field except "Approved by" and "Approval date".
4. Keep the scope narrow: name the exact package and version, the files or the rule.
5. Write in short, plain sentences (`asd-ste100` skill).

## Step 3. Draft the matching tool configuration, if needed

Some findings need a configuration entry with the **same** expiry date. Draft it, but do not merge it without the approved record.

| Finding | Configuration |
|---|---|
| Licence outside the allowlist | `[[PackageOverrides]]` in `policy-config/osv-scanner.toml` with `name`, `ecosystem`, `license.override` or `license.ignore = true`, `effectiveUntil` and `reason = "EXC-NNN: ..."` |
| Known advisory without a fix | `[[IgnoredVulns]]` in `policy-config/osv-scanner.toml` with `id`, `ignoreUntil` and `reason = "EXC-NNN: ..."` |
| Guardrail finding on a governance change | No configuration. Put the exception path in the `Exception:` line of the pull request. |

## Step 4. Hand over

Tell the user:

- the file path
- that the risk owner must fill in "Approved by" and "Approval date"
- the line to put in the pull request: `Exception: governance/exceptions/EXC-NNN-<short-name>.md`
- the expiry date. A weekly job reminds the owner 14 days before it.

Never approve the exception yourself. Never set an expiry date further than the user asked for.
