# Evaluation Run <YYYY-MM-DD> — <host or platform>

| Item | Value |
|---|---|
| Date | YYYY-MM-DD |
| Repository commit | <sha> |
| Host | GitHub (public repository) / local |
| Runner image | <for example ubuntu-24.04, from the job log> |
| Tools | Python <v>, Semgrep <v>, gitleaks <v>, OSV-Scanner <v> |
| Agent platform | <Claude Code vX / VS Code vX + Copilot vX / none> |
| Operating system for agent runs | <macOS / Linux / WSL2, version> |
| Settings | <profile file and settings commit> |
| Reviewer account separate from author | yes / no |

| Scenario | Expected | Observed | Evidence (link or file) | Residual risk |
|---|---|---|---|---|
| S01 | Requires human review | | | |
| S02 | Detected (Blocked if required) | | | |
| S03 | Detected | | | |
| S04 | Detected (Blocked if required) | | | |
| S05 | Not covered | | | |
| S06 | Detected | | | |
| S07 | Not covered | | | |
| S08 | Detected | | | |
| S09 | Detected + Requires human review | | | |
| S10 | Blocked | | | |
| S11 | Blocked until owner approves | | | |
| S12 | Blocked | | | |
| S13 | Blocked or Requires human review | | | |
| S14 | Blocked by containment, or Not covered | | | |

## Changes made during the run

<Rule or setting changes, and the scenarios run again after each change. Write "None" if there were no changes.>
