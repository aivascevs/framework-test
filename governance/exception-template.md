# Exception Record (C8)

Copy this file to `governance/exceptions/EXC-<number>-<short-name>.md`. Link it from the pull request. An exception accepts a residual risk for a limited scope and time. It does not remove the finding.

| Field | Value |
|---|---|
| Exception ID | EXC-000 |
| Pull request or change | <link> |
| Control and finding | <for example: C5 — licence `GPL-3.0-only` for package `example` is outside the allowlist> |
| Risk class of the change | Routine / Elevated / High impact / Restricted |
| Residual risk | <what can still go wrong> |
| Justification | <why the change continues> |
| Compensating measures | <what reduces the risk> |
| Scope | <which files, packages or versions> |
| Approved by | <name and role of the risk owner> |
| Approval date | YYYY-MM-DD |
| Expiry or review date | YYYY-MM-DD |
| Tool configuration change | <for example: `[[PackageOverrides]]` entry in `policy-config/osv-scanner.toml` with the same expiry, or "none"> |

## Lessons learned

<After the expiry date, or after an incident: what did we learn? Which policy, template or check must change?>
