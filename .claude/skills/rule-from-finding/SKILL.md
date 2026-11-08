---
name: rule-from-finding
description: Turn a review finding, an incident or a missed defect into a new Semgrep rule with a test file. Then CI detects the same pattern next time. Use when the user invokes /rule-from-finding or asks to add a check for a code pattern that was found in a review.
argument-hint: "<finding: file and line, or a short description of the unsafe pattern>"
---

# Rule from Finding

This skill closes the feedback loop of the lifecycle (stage 7). A finding becomes a rule, and every later pull request is checked for it. Example: evaluation scenario S06 found that the SQL rule missed adjacent f-strings. The rule now covers that form, and its test file contains the case.

Mode: Manual (a person asks for the rule and reviews it). The rule itself works in CI as Detected.

## Step 1. Understand the finding

1. Read the finding and the code it points to.
2. Write the unsafe pattern in one sentence. Example: "SQL text built from a value with an f-string, passed to `execute()`."
3. Write one safe form of the same code. Example: "`execute()` with `?` placeholders and a parameter tuple."
4. If the finding contains secrets or personal data, follow the `sensitive-data-guard` skill. Do not copy real values into the rule or the test.

## Step 2. Write the rule

1. Choose the rule file by language: `policy-config/semgrep/python.yaml`, `csharp.yaml` or `typescript.yaml`. Create a new file for a new language.
2. Add one rule. Use the style of the existing rules:
   - `id`: `<language>-<short-name>`
   - `severity`: `ERROR` when the pattern must block the merge, `WARNING` when a reviewer decides
   - `message`: what is wrong and what to do instead, in two short sentences
   - `metadata`: `cwe`, `control` (C3 or C4) and `requirement` (SEC or DATA)
3. Prefer `metavariable-pattern` when the unsafe value can appear in more than one form.
4. Do not copy rules from the Semgrep registry. Registry rules have their own licence.

## Step 3. Write the test

Add cases to the test file with the same base name in `tests/fixtures/semgrep/` (for example `python.py`):

- at least two lines marked `# ruleid: <id>` with the unsafe forms, including the form from the finding
- at least one line marked `# ok: <id>` with the safe form

## Step 4. Run the checks

If you can run commands:

```bash
semgrep --test --metrics=off --config policy-config/semgrep tests/fixtures/semgrep
semgrep scan --config policy-config/semgrep --metrics=off --error sample-app scripts
```

1. The rule test must pass.
2. The scan of the existing code must stay clean. If the new rule reports existing code, show the findings to the user. Do not weaken the rule to hide them.

If you cannot run commands, give the user these commands.

## Step 5. Hand over

The change touches `policy-config/`, so it is a governance change. It needs code-owner review. Tell the user:

- the rule id and the file
- the test cases you added
- the result of both commands, or that they did not run
- that the pull request needs review by the governance owner
