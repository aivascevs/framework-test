# Controls and Assurance Modes

This file lists every control of the framework, the artefact in this repository that implements it, and the assurance that the artefact can give. Chapter 5 of the thesis reports the observed results. The modes below are the **intended** modes. A test result does not upgrade a mode.

## 1. Assurance modes

| Mode | Meaning |
|---|---|
| **Enforced** | A technical limit stops an action or a transition when its conditions are met. Use this label only after a test showed the behaviour. |
| **Detected** | A check finds a condition and reports it. The change stops only if a required check or an approval rule prevents the merge. |
| **Advisory** | A policy, a template or an instruction asks for a behaviour. It does not prevent the opposite. |
| **Manual** | A person does an action or makes a decision. |

One control can use more than one mode. Example: the CI scanner **detects** a licence finding. The repository rule **enforces** that the merge waits, but only if the check is required and nobody can bypass it. A qualified person **manually** decides if the licence is acceptable.

Evaluation results use four categories: **Blocked**, **Detected**, **Requires human review** and **Not covered**. See [evaluation/protocol.md](../evaluation/protocol.md).

## 2. Core controls (all AI-assisted changes)

| ID | Control | Minimum expectation | Responsible role | Artefact in this repository | Mode | Limitation |
|---|---|---|---|---|---|---|
| C1 | Approved tool and data-use rules | Name the permitted AI services, modes, data classes and provider conditions | Governance or security owner | [`governance/approved-tools.yaml`](approved-tools.yaml) | Advisory | A repository file cannot stop the use of personal accounts |
| C2 | Change specification and risk classification | Record the purpose, acceptance criteria, affected components, data and security needs, owner and risk class | Change author. Technical lead approves Elevated and above. | [`new-change` skill](../.claude/skills/new-change/SKILL.md), [`specs/_template/spec.md`](../specs/_template/spec.md), [`plan.md`](../specs/_template/plan.md), [`risk-paths.yaml`](../policy-config/risk-paths.yaml), [`scripts/check_metadata.py`](../scripts/check_metadata.py), risk-drift check in [`scripts/check_guardrails.py`](../scripts/check_guardrails.py) | Advisory (skill, templates). Detected (scripts). | The check shows that fields exist and that the class is not below the path minimum. It does not show that the class is correct. |
| C3 | Data minimisation and context boundary | Give only the context that the task needs. No secrets or restricted data without authorisation. | Developer or agent operator | [`governance/data-handling.md`](data-handling.md), spec data-class field, [`sensitive-data-guard` skill](../.claude/skills/sensitive-data-guard/SKILL.md), "Secrets and personal data" job, `prompt_guard.py` hook (Claude Code CLI) | Manual and Advisory (prompts in the IDE). Detected (added lines). Enforced in the CLI if tested. | Patterns find formats, not meaning. Prompts typed in the IDE chat are not checked. |
| C4 | Security and quality verification | Run the tests and the security checks that the release policy requires | Engineering or security owner | [`governance.yml`](../.github/workflows/governance.yml): tests, Semgrep rules, gitleaks, removed-test and suppression flags. [`reviewer` agent](../.claude/agents/reviewer.md). [`rule-from-finding`](../.claude/skills/rule-from-finding/SKILL.md). | Detected. Flags: Requires human review. | Tools miss errors and report false positives. The reviewer agent is input, not proof. |
| C5 | Dependency and licence review | Check new or changed dependencies for known vulnerabilities and licence policy. Escalate unclear code origin. | Dependency or security owner. Legal or IP specialist when needed. | [`dependency-check` skill](../.claude/skills/dependency-check/SKILL.md) (before install), [`governance.yml`](../.github/workflows/governance.yml): OSV-Scanner, [`allowed-licenses.txt`](../policy-config/allowed-licenses.txt), [`osv-scanner.toml`](../policy-config/osv-scanner.toml) | Advisory (skill). Detected (CI). Manual (decision). | Package scanning cannot prove the origin of generated snippets |
| C6 | Accountable human review | A named human reviews and accepts the change. High impact changes need a qualified reviewer. | Code owner or designated reviewer | [`CODEOWNERS`](../.github/CODEOWNERS), [`ruleset.json`](../.github/ruleset.json), [`docs/review-checklist.md`](../docs/review-checklist.md) | Enforced (host, if configured) and Manual | The log shows that an approval happened, not the quality of the review |
| C7 | Change disclosure and evidence | Record the AI tool and mode, and the checks and decisions that explain the change. Do not claim line-level authorship. | Change author and repository owner | Specification front matter (CI reads it), [PR template](../.github/pull_request_template.md), [`scripts/evidence_summary.py`](../scripts/evidence_summary.py), [`docs/evidence-format.md`](../docs/evidence-format.md) | Advisory and Detected (record) | The AI-use declaration is self-reported |
| C8 | Exception and feedback process | Record the residual risk, approver, justification, scope, expiry and lessons | Risk owner and service owner | [`exception-drafter` skill](../.claude/skills/exception-drafter/SKILL.md), [`governance/exception-template.md`](exception-template.md), `[[PackageOverrides]]` with `effectiveUntil` in `osv-scanner.toml`, weekly [`governance-reminders.yml`](../.github/workflows/governance-reminders.yml) | Manual. Reminders: Detected. | Needs organisational follow-through |
| C9 | Reviewability gate | Keep each change small enough for a full review by a qualified reviewer. Split larger changes into increments in the specification. Run automated checks before the human review. | Technical lead and code owner | [`review-budget.yaml`](../policy-config/review-budget.yaml), size check in [`scripts/check_guardrails.py`](../scripts/check_guardrails.py), increments in section 8 of [`spec.md`](../specs/_template/spec.md), [`change-splitter` skill](../.claude/skills/change-splitter/SKILL.md), review order from the [`reviewer` agent](../.claude/agents/reviewer.md) and the evidence summary, `scope_guard.py` new-file limit (CLI) | Detected (CI). Enforced at merge if the check is required. Advisory (skill, review order). | Line count only approximates review effort. The AI review order is advice, not an approval. |

Dependency checking is not the same as provenance of generated code. Software composition analysis shows components, vulnerabilities and declared licences. It does not show that generated code is original, or that it does not infringe a copyright or a licence. In the same way, an AI-use declaration helps the reviewer. It does not prove authorship.

## 3. Agentic extensions (apply by capability)

| ID | Capability trigger | Control | Preferred control point | Artefact in this repository | Mode | Limitation |
|---|---|---|---|---|---|---|
| A1 | Agent can modify files | Write only in the task workspace. Deny credentials, hooks and governance configuration. | OS or platform sandbox, permission rules | [`.claude/settings.json`](../.claude/settings.json), [`.vscode/settings.json`](../.vscode/settings.json), `scope_guard.py` hook (CLI), scope check in `check_guardrails.py` | Enforced only for the tested tool path. Detected (CI scope). Otherwise Advisory. | Claude Code sandbox covers Bash only. Read, Edit and Write use permission rules. The hook runs in the CLI only. |
| A2 | Agent can run commands | Limit commands. Ask before install, delete, privilege change. | Agent permission system, isolated execution | Same files | Enforced if tested | Pattern rules can miss wrappers (`sh -c`) |
| A3 | Agent can access a network | No network or an approved allowlist | Sandbox network proxy, firewall | Same files. Copilot cloud agent: repository firewall setting. | Enforced if tested | A hostname allowlist does not inspect TLS. A broad allowed domain can carry data out. |
| A4 | Agent can access credentials | No production credentials. Short-lived test credentials only. | Secret management, execution environment | `sandbox.credentials` and `Read` deny rules. `prompt_guard.py` hook (CLI). | Enforced if tested | Show that credentials are absent by setup, not by instruction |
| A5 | Agent can use external tools or MCP servers | Deny by default. Approve per server. Least privilege. No token passthrough. | Platform configuration | [`docs/extensions/mcp.md`](../docs/extensions/mcp.md). `check_agent_config.py` fails if `.mcp.json` or `.vscode/mcp.json` appears. | Advisory (reference only). Detected (no MCP file). | Not demonstrated |
| A6 | Agent reads untrusted content | Untrusted content cannot authorise privileged operations | Task design, permission boundaries | [`AGENTS.md`](../AGENTS.md), containment through A1–A3 | Advisory. Containment depends on A1–A3. | Prompt-injection detection is not reliable |
| A7 | Agent configuration affects behaviour | Code-owner review for instructions, workflows and permission profiles | CODEOWNERS and ruleset | [`CODEOWNERS`](../.github/CODEOWNERS), [`check_agent_config.py`](../scripts/check_agent_config.py) with [`agent-baseline.yaml`](../policy-config/agent-baseline.yaml) | Enforced at merge if code-owner review is required. Detected (baseline). | Protects the repository files, not user or managed settings or external content |
| A8 | Agent does multi-step work | The operator can monitor, stop and approve capability increases | Agent platform, change workflow | `defaultMode: plan` (Claude Code), read-only [`planner` agent](../.claude/agents/planner.md), [`governed-change` skill](../.claude/skills/governed-change/SKILL.md) | Enforced in Claude Code if tested. Advisory in Copilot. Manual (approval). | Session logs can be incomplete. Copilot has no repository setting for plan mode. |
| A9 | Agent can push, merge or deploy | Deny by default. Human approval and the normal release process. | Repository and deployment permissions | [`ruleset.json`](../.github/ruleset.json), `Bash(git push *)` deny rule | Enforced if the agent identity has no bypass permission | A draft pull request is not a deployment |

## 4. Control points and demonstrator treatment

| Control area | Core or extension | Control point | Mode | Effect and condition | Treatment | Evidence |
|---|---|---|---|---|---|---|
| Approved tools and data rules | Core | Governance | Advisory | Enforced only when tool access is centrally restricted | Configure | Versioned register |
| Specification fields and AI-use declaration | Core | Specification and PR | Detected | Merge stops only when the metadata check is required | Test | Specification and check result |
| Change size and increments (reviewability gate) | Core | Specification and CI | Detected | Merge stops only when "Change guardrails" is required. An exception can accept an over-budget change. | Test | Size result, review order, exception record |
| Data minimisation | Core | Human and platform | Manual | Platform enforcement varies. Do not assume complete detection of sensitive data. | Document | Data-class decision. No raw prompts by default. |
| Agent file, command and network permissions | Extension | Agent platform | Enforced or Advisory | Claim enforcement only for tested permissions and configuration | Test | Versioned profile and observed denial or approval |
| Secret scanning | Core | CI | Detected | Can block the merge when the check is required | Test | Scan result linked to the commit |
| Dependency and security checks | Core | CI | Detected | Blocks the merge only when the check is required. Scanner coverage is limited. | Configure | Check result |
| Licence and IP decision | Core | CI and human review | Detected and Manual | The tool reports a finding. A qualified person decides. | Test | Finding and human decision |
| Human review and protected integration | Core | Source-control host and reviewer | Enforced and Manual | The host can require approval. Review quality stays a human task. | Configure | Approval and merge record |
| MCP and external tools | Extension | Agent platform | Advisory | Deny by default | Exclude | Approved-server record, if enabled later |
| Release and incident feedback | Core | Operations | Manual | Uses the existing release and incident process | Document | Release or incident link and review note |

Treatment labels: **Configure** = part of the repository. **Test** = exercised with a safe fixture in `evaluation/`. **Document** = written guidance only. **Exclude** = reference only, no live integration.
