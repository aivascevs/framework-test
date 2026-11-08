---
name: sensitive-data-guard
description: Use whenever a prompt, a file, a log, a ticket or tool output contains or may contain secrets or personal data. Secrets: keys, tokens, passwords, connection strings. Personal data: e-mail addresses, phone numbers, personal codes, IBANs, card numbers, real names in test data. Also use before you propose a commit or write pull request text. Stops sensitive data from spreading into code, tests, logs, commits and pull requests.
---

# Sensitive Data Guard

This skill limits the **spread** of sensitive data. It cannot stop the **first** exposure: when you see the data, the model provider already received it. Prevention of that first exposure is an organisational control (approved tools, managed settings, training). See `governance/data-handling.md`.

Mode: Advisory. CI repeats the pattern check on every pull request (job "Secrets and personal data").

## Step 1. When you see sensitive data in input

The input can be a prompt, a file, a pasted log, a ticket or tool output.

1. Stop the current step.
2. Do not repeat the value. Do not quote it in chat, in a plan or in any file.
3. Tell the user the **kind** of data and the **location** (file and line, or "your message"). Example: "Your message contains what looks like an API key. Line 3 of the pasted log contains two e-mail addresses."
4. If the data is a key, a token or a password, tell the user to rotate it. The model provider received it.
5. Check the data class. Read `data_class` in the specification and `max_data_class` for your tool in `governance/approved-tools.yaml`. If the task needs data above that class, stop. Tell the user that the task needs a human process or an approved exception.
6. Continue the task only with synthetic stand-ins.

## Step 2. While you write code, tests and text

- Never copy a real value into code, tests, fixtures, logs, comments, commit messages, pull request text or the evidence summary.
- Use synthetic values:
  - e-mail addresses on reserved domains: `ana@example.test`, `ben@example.com`
  - the documentation IBAN `GB82 WEST 1234 5698 7654 32` <!-- sensitive-data: synthetic -->
  - the test card number `4111 1111 1111 1111` <!-- sensitive-data: synthetic -->
  - obviously fake keys such as `test-key-not-real`
- Read secrets from configuration or environment variables. Never write them as literals.
- Do not write personal data to logs. Mask it, for example with `mask_email()`.
- Mark a deliberately synthetic value that looks real with the comment `sensitive-data: synthetic` on the same line. CI reports every new marker to the human reviewer.

## Step 3. Before you propose a commit or a pull request

Run the bundled scanner on your own changes:

```bash
python .claude/skills/sensitive-data-guard/scripts/scan_sensitive.py --worktree
```

- Exit code 0: no pattern found. Say that the scan found nothing. Do not say that the change contains no sensitive data.
- Exit code 1: fix each finding. Replace the value with a synthetic value or a configuration read. Run the scanner again.
- If you cannot run commands (capability profile P1, or plan mode), tell the user to run it, or rely on the CI job.

## What the scanner covers

| Kind | Rules |
|---|---|
| Secrets | private key headers, AWS access key IDs, GitHub tokens, JWTs, connection-string passwords, credential assignments |
| Personal data | e-mail addresses (not on reserved domains), IBANs (checksum), payment cards (Luhn), Latvian personal codes (checksum), phone numbers |

The scanner prints the kind and the location, never the value. It finds only these formats. It does not find real names, addresses or free-text personal data. You must still judge those yourself.

## Report

When you finish, state in one line what you checked. Example: "Sensitive-data scan on 3 changed files: no pattern found. Names in test data are synthetic."
