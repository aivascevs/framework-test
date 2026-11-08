# Development Smoke Test 2026-10-26

**Status: development check, not a thesis evaluation run.** The protocol was still being written when the first run happened, so this record does not meet the rule "commit the protocol before you run". Use it as a check that the scripts and fixtures work. Run the formal evaluation on the source-control host with a copy of `results-template.md`.

Environment: local Linux container without access to OSV.dev or deps.dev. Host scenarios (S03, S10, S11) and agent scenarios (S12–S14) were not run.

## Change during development

The first run reported S06 as **Not covered**. The rule `python-sql-built-from-strings` matched one f-string in `execute()`, but not two adjacent f-strings over two lines. The rule now uses `metavariable-pattern`, and its test file contains the multi-line case (`tests/fixtures/semgrep/python.py`). This is an example of the expected limitation: a rule finds only the forms that it describes.

When OSV-Scanner cannot reach its databases, it exits with code 127. The CI job then fails. It does not pass without a scan.

## Run after the change

Commit: `0ba995c`

Tools: python 3.13.16, os Linux-6.18.44-fc-v153-x86_64-with-glibc2.39, semgrep 1.180.0, gitleaks 8.30.1, osv-scanner osv-scanner version: 2.7.0, pytest pytest 9.1.1

| Scenario | Title | Checks | Expected | Observed | Match |
|---|---|---|---|---|---|
| S01 | Conforming change | metadata: pass, tests: pass, sast: pass, secrets: pass | Requires human review | Requires human review | yes |
| S02 | PR misses risk class and specification link | metadata: fail | Detected | Detected | yes |
| S04 | Synthetic secret that matches a rule | secrets: fail, sast: fail | Detected | Detected | yes |
| S05 | Synthetic secret in a format no rule covers | secrets: pass, sast: pass | Not covered | Not covered | yes |
| S06 | Seeded SQL injection covered by a rule | sast: fail, tests: pass | Detected | Detected | yes |
| S07 | Missing authorisation check, no rule | sast: pass, tests: pass | Not covered | Not covered | yes |
| S08 | Dependency version with a published advisory | dependencies: not run (network) | Detected | Not run in this environment | n/a |
| S09 | Dependency licence outside the allowlist | dependencies: not run (network) | Detected + Requires human review | Not run in this environment | n/a |

Local runs cannot show host blocking (S03, S10, S11). Agent scenarios (S12-S14) are manual. See evaluation/protocol.md.
