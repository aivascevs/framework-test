# Alignment with the Thesis (Chapter 4)

This document maps Chapter 4 of the thesis "Governance for secure and compliant AI code generation" (version of 2026-11-07) to the files in this repository. Use it to check that the text and the demonstrator say the same thing.

Status values:

- **Match**: the repository does what the thesis describes.
- **Beyond**: the repository does more than the thesis describes. Update the thesis, or keep the extra part as optional.
- **Differs**: the repository and the thesis say different things. One of them must change.
- **Gap**: the thesis describes it, and the repository does not have it.

## 1. Design principles (section 4.3)

| # | Principle | Repository | Status |
|---|---|---|---|
| 1 | Govern the change, not the AI authorship | [`governance/policy.md`](../governance/policy.md) §2.1 | Match |
| 2 | Apply controls that match the risk | Policy §2.2, [`risk-and-capability.md`](../governance/risk-and-capability.md) | Match |
| 3 | Keep guidance separate from enforcement | Policy §2.3, assurance modes in [`controls.md`](../governance/controls.md) | Match |
| 4 | Least privilege and bounded autonomy | Policy §2.4, capability profiles P0–P3, [`agent/`](../agent/README.md) | Match |
| 5 | Independent checks and proportionate evidence | Policy §2.5, CI, [`evidence_summary.py`](../scripts/evidence_summary.py). No raw prompts kept. | Match |
| 6 | Make human accountability visible | Policy §2.6 and §3, `risk_confirmed_by`, CODEOWNERS | Match |
| 7 | Delegate only up to the reviewing capability | Policy §2.7, [`review-budget.yaml`](../policy-config/review-budget.yaml), increments in the specification, [`change-splitter`](../.claude/skills/change-splitter/SKILL.md) | Match (added 2026-11-07) |

## 2. Risk classes (Table 4.2) and lifecycle (Table 4.3)

| Thesis | Repository | Status |
|---|---|---|
| Routine, Elevated, High impact, Restricted | [`risk-and-capability.md`](../governance/risk-and-capability.md), `risk_class` in the specification, minimum class by path in [`risk-paths.yaml`](../policy-config/risk-paths.yaml) | Match. The path minimum is Beyond. |
| "The classification of risk is to be made by people, not by an AI agent" (§4.2) | The `new-change` skill **proposes** a class with reasons. The change author sets it. The technical lead approves Elevated and above (`risk_confirmed_by`). CI only checks that the class is not below the path minimum. | Differs in wording. Suggested thesis text: "An agent may propose a class with its reasons. A person decides and records the class." |
| Stages 0–7 | [FRAMEWORK.md §3](FRAMEWORK.md#3-lifecycle-of-a-governed-change), three human gates in [FRAMEWORK.md §3.1](FRAMEWORK.md#31-day-to-day-flow-three-human-gates) | Match |
| Step 2 splits large work into reviewable increments | Section 8 of [`spec.md`](../specs/_template/spec.md), `change-splitter` skill, planner size estimates | Match |
| Step 5: deterministic checks first, then an AI reviewer ranks high-risk components | Five CI checks. Review order in the evidence summary (by path risk and size). The `reviewer` agent gives its own ranked order before the pull request. | Match. The AI reviewer runs in the developer's session, not in CI (see C9). |
| Step 6: the human reviews inside the change budget, high-risk components first | [`review-checklist.md`](review-checklist.md) §2, evidence summary "Size and review order" | Match |

## 3. Core controls (Table 4.4)

| ID | Thesis minimum expectation | Repository artefacts | Mode in the repository | Status |
|---|---|---|---|---|
| C1 | Approved tools and data rules | [`approved-tools.yaml`](../governance/approved-tools.yaml), weekly review reminder | Advisory, reminder Detected | Match |
| C2 | Specification and risk classification | `new-change` skill, spec template, [`check_metadata.py`](../scripts/check_metadata.py), risk-drift check | Advisory and Detected | Beyond (skill, risk drift) |
| C3 | Data minimisation and context boundary | [`data-handling.md`](../governance/data-handling.md), `sensitive-data-guard` skill and scanner, "Secrets and personal data" job, CLI prompt hook | Manual and Advisory for prompts in the IDE. Detected for added lines. Enforced in the CLI if tested. | Beyond. Table 4.6 says "Manual/advisory" only. |
| C4 | Security and quality verification | pytest, Semgrep (own rules), gitleaks, removed-test and suppression flags, `rule-from-finding` | Detected | Beyond (flags, rule skill) |
| C5 | Dependency and licence review | `dependency-check` skill (invented packages, age, licence, advisories), OSV-Scanner, licence allowlist | Advisory, Detected, Manual | Beyond (pre-install skill) |
| C6 | Accountable human review | CODEOWNERS, [`ruleset.json`](../.github/ruleset.json), review checklist | Enforced (host, if configured), Manual | Match |
| C7 | Change disclosure and evidence | Specification front matter (CI reads it), evidence summary | Advisory, Detected (record) | Differs: see §6, item 2 |
| C8 | Exception and feedback process | Exception template, `exception-drafter` skill, scanner overrides with expiry, weekly reminders | Manual, reminders Detected | Beyond (skill, reminders) |
| C9 | Reviewability gate | [`review-budget.yaml`](../policy-config/review-budget.yaml), size check in [`check_guardrails.py`](../scripts/check_guardrails.py) (`review-budget`, `new-file-size`), increments in section 8, `change-splitter` skill, review order, CLI new-file limit | Detected. Enforced at merge if "Change guardrails" is required. | Match. The "optional AI-review job" is in the session, not in CI (see §6, item 4). |

### C9 budget values

The defaults are:

- Routine: 400 changed lines, 20 files
- Elevated: 400 changed lines, 15 files
- High impact: 200 changed lines, 8 files
- One new file: 300 lines

They follow common guidance that reviews find fewer defects above about 200–400 lines in one session. An example source is the SmartBear and Cisco code-review study. Present the values in the thesis as team settings, not as measured limits. Table 4.4 already says this: "number of lines is just an approximation of reviewing effort".

## 4. Agentic extensions (Table 4.5)

| ID | Repository | Status |
|---|---|---|
| A1 | Claude Code sandbox and permission rules, VS Code agent sandbox (preview), CI scope check, CLI `scope_guard.py` | Beyond (CI scope, increment scope) |
| A2 | Permission rules, terminal approval rules | Match |
| A3 | Sandbox network allowlist, Copilot cloud agent firewall | Match |
| A4 | `sandbox.credentials`, read deny rules, CLI `prompt_guard.py` | Beyond (prompt hook) |
| A5 | [`docs/extensions/mcp.md`](extensions/mcp.md). CI fails if an MCP file appears. | Match (reference only), plus a detection |
| A6 | `AGENTS.md`, containment through A1–A3, S14 fixture | Match |
| A7 | CODEOWNERS, [`check_agent_config.py`](../scripts/check_agent_config.py) with [`agent-baseline.yaml`](../policy-config/agent-baseline.yaml) | Beyond. Table 4.6 names CODEOWNERS only. |
| A8 | Plan mode by default (Claude Code), read-only `planner` agent, plan approval | Beyond |
| A9 | Ruleset, `git push` deny rule | Match |

## 5. Scenarios (Table 4.8) and the protocol

| Table 4.8 scenario | Protocol ID | Status |
|---|---|---|
| A change that follows the rules | S01 | Match |
| PR without a specification link or risk class | S02 | Match |
| Synthetic secret in a fixture | S04 (S05 is the negative control: a format no rule covers) | Match |
| Insecure pattern covered by a test or rule | S06 (S07 is the negative control) | Match |
| Lockfile with a known advisory | S08 | Match (needs network) |
| Licence outside the allowlist | S09 | Match (needs network) |
| Harmless write outside the workspace or to a protected path | S12, S23 | Match |
| Command or network request outside the profile | S27 (command), S13 (network) | Match (S27 added 2026-11-07) |
| Conflicting instruction in a README fixture | S14 | Match |
| Merge without the required approval | S10 | Match |
| — | S03: as S02, but the check is not required (shows Detected without Blocked) | Beyond |
| — | S11: pull request changes `AGENTS.md` (A7) | Beyond |
| Over-budget pull request without an exception | S24 (and S25 with an exception, S26 large new file) | Match |
| — | S15–S19: scope, risk drift, removed tests and suppressions, weakened agent settings, personal data | Beyond. Add to Table 4.8, or name them as extra scenarios. |
| — | S20–S23: invented package, skills and read-only agents, CLI hooks | Beyond |

Check the S-numbers against [`evaluation/protocol.md`](../evaluation/protocol.md) before you cite them. The protocol is the source.

## 6. Thesis text that is behind the repository

1. **One platform (§4.1).** "The demonstrator ... along with one agent platform." The repository supports Claude Code and GitHub Copilot in VS Code, with setup scripts for both.
2. **AI-use field in the PR (§4.10).** "A pull request then references the specification and contains an AI use field." Now the pull request has only `Specification:`, `Increment:` and `Exception:`. CI reads the AI use, tool, profile, risk class and data class from the specification. This removes double entry. The light path (`Specification: none`) keeps the fields in the PR for Routine changes with suggest-only AI.
3. **Evidence per commit (§4.10).** "Every commit has a corresponding evidence summary." The summary is made for the head commit of each pull request.
4. **AI-review job (Table 4.6, C9).** The thesis names an "optional AI-review job" in CI. The repository has the read-only `reviewer` agent in the developer's session and a deterministic review order in CI. An AI job in CI would need a provider key in CI secrets and would send code to the provider on each pull request. It stays optional and is not in the demonstrator.
5. **Figure 4.4.** The component view shows four checks and the evidence summary. The repository has a fifth required check, **Change guardrails** (scope, risk drift, change size C9, agent configuration). C9 needs it, because the size check is in that job. See [`06-c4-component-ci`](diagrams/06-c4-component-ci.svg).
6. **Section 4.9.3.** "List the name of scanner with its version only once it is selected and tested." They are selected: gitleaks CLI 8.30.1, OSV-Scanner 2.7.0, Semgrep CE 1.180.0 ([`NOTICE.md`](../NOTICE.md)).
7. **Sandbox wording (after Table 4.5).** "Claude Code sandbox allows the use of shell command, whereas file edit, hooks, and MCP processes use other sandbox controls." More exact: the sandbox covers Bash commands and their child processes. The Read, Edit and Write tools use permission rules. Hooks and local MCP servers run outside the sandbox.
8. **New elements not in Chapter 4:** the skills (`new-change`, `sensitive-data-guard`, `dependency-check`, `change-splitter`, `rule-from-finding`, `exception-drafter`), the read-only agents, the CLI hooks, the weekly reminders and the setup scripts. A short paragraph in §4.8 and one row each in Table 4.6 are enough.

## 7. Editorial notes on the 2026-11-07 version

| Location | Text | Suggestion |
|---|---|---|
| Title page and file name | "complaint" | "compliant" |
| Table of contents, 4.9.1 | "System contex" | "System context" |
| Table 4.2, header | "Proposed class risk class" | "Proposed risk class" |
| Table 4.5, title and header | "Govenrance", "Capbility", "Preffered" | "Governance", "Capability", "Preferred" |
| Table 4.5, A5 | "servers/toold" | "servers/tools" |
| §4.7 | "Table 4.5 uses the assurance classification" and "Table 4.6 provides the assurance mode" | The mapping table is Table 4.6 in §4.8. No table has the number 4.7. Renumber, or point both sentences to the right table. |
| §4.4 | Caption "Figure 4.1. Intake and classification" | "Figure 4.1. Governed change lifecycle" |
| §3.3 | "Figure 1 Lifecycle Placement of Governance Priorities" | "Figure 3.5 ..." |
| §4.10 | "seeting", "parametrs", "wont", "what was created" | "settings", "parameters", "will not", "which was created" |
| Table 4.8, row "merge without approval" | Empty nested table in the Evidence cell | Replace with plain text "Host response and review record" |
