---
name: dependency-check
description: Use before you propose, add or install any third-party package (PyPI, npm, NuGet), and before you copy code from an external source. Checks that the package exists, that the version exists, how old it is, its declared licence and its known advisories. Prevents invented package names and licence surprises.
---

# Dependency Check

Language models sometimes propose packages that do not exist. An attacker can register such a name and publish harmful code ("slopsquatting"). Licences can also make a package unusable. This skill checks a package **before** it enters the plan or the code. CI checks the dependencies again on the pull request (job "Dependencies and licences").

Mode: Advisory. The human reviewer decides on every finding.

## Step 1. Prefer what the project already has

1. Read the manifests (`requirements.txt`, `pyproject.toml`, `package.json`, `*.csproj`).
2. If an existing dependency can do the job, use it. Do not add a new package.
3. A new package needs a reason in the plan.

## Step 2. Check each new package

Run the bundled checker with the exact version:

```bash
python .claude/skills/dependency-check/scripts/check_package.py pypi requests==2.32.3
python .claude/skills/dependency-check/scripts/check_package.py npm zod@3.23.8
python .claude/skills/dependency-check/scripts/check_package.py nuget Newtonsoft.Json@13.0.3
```

If you cannot run commands (profile P1, or plan mode), give the user the command. Do not guess the result.

## Step 3. Act on the result

| Result | Action |
|---|---|
| Package does not exist | Do not install it. Do not try similar names. Check the official documentation for the correct name, and tell the user. |
| Version does not exist | Use a version that exists. Prefer the latest version without advisories. |
| Known advisories | Choose a version without the advisory. If none exists, tell the user and stop. |
| First release less than 90 days ago | Tell the user. A human decides before the package goes into the plan. |
| Licence not in `policy-config/allowed-licenses.txt` | Do not install it. Tell the user. A human decides and records an exception (`/exception-drafter`). |
| Licence not an SPDX identifier, or not declared | Tell the user. A human checks the upstream licence file. |
| Advisories not checked (no network) | Say so. CI checks them on the pull request. |

## Step 4. Record the decision

Add one row per package to the "New dependencies" table in `plan.md`: package, exact version, licence, why it is needed, checker result. Pin the exact version in the manifest.

## Copied code

If you copy or closely adapt code from documentation, a repository or a forum:

- Record the source URL and its licence in the pull request text.
- Keep the copyright and licence notice.
- Do not copy code from sources with a licence that is not in the allowlist.
- Forum answers (for example Stack Overflow, CC BY-SA) need attribution. Prefer to write the code yourself.

## Limits

The checker reads registry metadata. It does not inspect the package code. A package that passes all checks can still be unsafe. Say what you checked, not that the package is safe.
