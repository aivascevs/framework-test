# Install and Use

This guide installs the framework into a project and shows the daily work with it. It covers Claude Code (CLI and VS Code extension) and GitHub Copilot (agent mode in VS Code, and the Copilot cloud agent).

For what the framework is and why, read [FRAMEWORK.md](FRAMEWORK.md). To test it on the sample application, read [TESTING.md](TESTING.md). Platform details are in [agent/README.md](../agent/README.md).

## Contents

- [1. What you get](#1-what-you-get)
- [2. Prerequisites](#2-prerequisites)
- [3. Install](#3-install)
- [4. Configure once](#4-configure-once)
- [5. Daily use: one change from start to merge](#5-daily-use-one-change-from-start-to-merge)
- [6. Special cases](#6-special-cases)
- [7. When a CI check fails](#7-when-a-ci-check-fails)
- [8. Platform differences](#8-platform-differences)
- [9. Update or uninstall](#9-update-or-uninstall)
- [10. Troubleshooting](#10-troubleshooting)

## 1. What you get

| Part | Files | Platform |
|---|---|---|
| Rules and templates | `governance/`, `specs/_template/`, `AGENTS.md` | Both |
| Skills and read-only agents | `.claude/skills/` (8 skills), `.claude/agents/` (`planner`, `reviewer`) | Both. VS Code reads the same folders. |
| Claude Code settings | `CLAUDE.md`, `.claude/settings.json`, `.claude/hooks/`, `agent/profiles/` | Claude Code |
| Copilot settings | `.vscode/settings.json` | GitHub Copilot in VS Code |
| CI | `.github/workflows/`, `scripts/`, `policy-config/` | GitHub Actions |
| Host rules | `.github/CODEOWNERS`, `.github/ruleset.json`, PR template | GitHub |

A developer uses only one command, `/new-change`, and three approvals. The rest runs in the agent and in CI.

## 2. Prerequisites

| Item | Needed for | Check |
|---|---|---|
| Git | Everything | `git --version` |
| Python 3.10 or later | Skill scanners, hooks, local checks | `python3 --version` |
| GitHub repository with Actions | CI checks | — |
| GitHub plan with rulesets | Blocking merges. Free for public repositories. Private repositories need a paid plan. | Settings, Rules |
| `gh` CLI (optional) | Applying the ruleset from the command line | `gh --version` |
| **Claude Code:** macOS, Linux or WSL2 | The sandbox. Native Windows has none. | `claude --version` |
| **Claude Code on Linux/WSL2:** `bubblewrap`, `socat` | The sandbox | `/sandbox` in Claude Code |
| **Copilot:** VS Code with GitHub Copilot Chat, organisation licence | Agent mode, skills | VS Code Extensions view |
| **Copilot on Linux/WSL2:** `bubblewrap`, `slirp4netns`, `util-linux`, `iptables` | Agent sandbox (preview) | — |

Check this machine without installing anything:

```bash
./setup.sh --check                    # macOS, Linux, WSL2
```

```powershell
.\setup.ps1 -Check                    # Windows
```

## 3. Install

Run the setup script from this repository. Give it the folder of your project.

```bash
./setup.sh /path/to/project                      # both platforms
./setup.sh /path/to/project --platform claude    # Claude Code only
./setup.sh /path/to/project --platform copilot   # GitHub Copilot only
./setup.sh /path/to/project --dry-run            # show what would happen
```

```powershell
.\setup.ps1 -Target C:\src\project
.\setup.ps1 -Target C:\src\project -Platform copilot
```

The script:

1. Checks the prerequisites.
2. Copies the framework files. It **never overwrites** a file. If a file exists, it writes `<file>.governance-new` next to it and lists it. Merge the two by hand, then delete the `.governance-new` file.
3. Sets the dependency scan to the whole project.
4. Adds `.active-spec` and `__pycache__/` to `.gitignore`.
5. Prints the next steps.

It does not change user settings, managed settings or repository settings on GitHub.

## 4. Configure once

A person with the right role does these steps once for each project.

| # | Step | File or place | Who |
|---|---|---|---|
| 1 | Replace the placeholder accounts | `.github/CODEOWNERS` | Repository owner |
| 2 | Set the owner, the data limit and the review date of each tool. Check `max_data_class` against your contract with the provider. | `governance/approved-tools.yaml` | Governance or security owner |
| 3 | Agree the licence allowlist | `policy-config/allowed-licenses.txt` | Legal or IP specialist |
| 4 | Add the risky paths of your project (authentication, payments, migrations, infrastructure) | `policy-config/risk-paths.yaml` | Technical lead |
| 5 | Set the change budget for each risk class, if the defaults do not fit | `policy-config/review-budget.yaml` | Technical lead |
| 6 | Add your build and test commands at "PROJECT TESTS" in the job "Tests and SAST" | `.github/workflows/governance.yml` | Developer |
| 7 | Add Semgrep rules for your languages, with a test file for each rule | `policy-config/semgrep/` | Security owner |
| 8 | Commit on a branch and open a pull request. Then apply the ruleset (below). | GitHub | Repository owner |
| 9 | Copilot cloud agent: keep the firewall on with the recommended allowlist | Repository Settings, Copilot, Internet access | Repository owner |
| 10 | Copilot Business or Enterprise: content exclusion for `**/.env*`, `**/secrets/**`, `**/*.pem`, and block suggestions that match public code | Organisation settings | Organisation owner |
| 11 | If the rules must hold against developers, copy the agent settings into managed settings | Managed settings of Claude Code and VS Code | IT or platform team |

Apply the ruleset after the first pull request has run the workflow once, so GitHub knows the check names:

```bash
gh api repos/OWNER/REPO/rulesets --method POST --input .github/ruleset.json
```

Or: Settings, Rules, Rulesets, New ruleset, Import a ruleset. Keep the bypass list empty. The ruleset requires one approval, code-owner review and five checks: Governance metadata, Change guardrails, Secrets and personal data, Dependencies and licences, Tests and SAST.

## 5. Daily use: one change from start to merge

This example adds a refund count per customer to the sample application. The same steps apply in Claude Code and in Copilot agent mode.

### Step 1. Start

Type in the agent chat:

```text
/new-change add a count of refunded orders per customer to the order store
```

The `new-change` skill reads the code and `policy-config/risk-paths.yaml`. It asks at most four questions, for example:

> Does the change read, store or show personal data? Can it be reversed easily? Does a contract restrict AI use for this work? What must never happen?

It then proposes, with reasons:

> Risk class **Elevated** (`sample-app/orders/**` is Elevated in risk-paths.yaml). Data class **internal**. Profile **P1 Edit**. One increment, about 80 changed lines.

It writes `specs/002-refund-count/spec.md` with `status: draft`.

### Step 2. Human gate 1: approve the specification

1. Read the draft. Check the acceptance criteria (AC), the security, data and licence requirements (SEC, DATA, LIC), the permitted files and the increments.
2. Change what is wrong.
3. Set `status: approved`.
4. For Elevated and above, the technical lead writes their name in `risk_confirmed_by`.

### Step 3. Human gate 2: approve the plan

Type: `plan the change`. The `governed-change` skill asks the read-only `planner` agent for a plan with size estimates. Read it and approve it.

- **Claude Code** starts in plan mode. It cannot edit files until you accept the plan.
- **Copilot** has no plan mode setting. The planner cannot edit, and the skill stops after the plan.

### Step 4. The agent works

After approval the agent:

1. Writes the tests first, then the code, one increment at a time.
2. Uses `dependency-check` before it adds a package, and `sensitive-data-guard` if it sees a key or personal data.
3. Asks the read-only `reviewer` agent for findings and a review order.
4. Runs the sensitive-data scan and the size check.
5. Writes the pull request text.

You approve commands and edits when the platform asks.

### Step 5. Open the pull request

The body needs only these lines. CI reads the risk class, the AI use and the other values from the specification.

```text
Specification: specs/002-refund-count/spec.md
Increment: INC-1
Exception: none
```

### Step 6. CI runs

Five required checks run, then the evidence summary. The summary shows the size of the change against the budget, a suggested review order (highest risk first) and the items that need a person.

### Step 7. Human gate 3: review and merge

A reviewer who did not prepare the change reads the files in the suggested order with the [review checklist](review-checklist.md), and approves. The ruleset lets the merge happen only after the approval and the required checks.

If the specification has more increments, start the next one with: `continue with the next increment`.

## 6. Special cases

| Case | What to do |
|---|---|
| **Small Routine change, AI only suggested code (light path)** | No specification is needed. Use this pull request body: `Specification: none`, `Risk class: Routine`, `AI use: suggest`, `AI tool: github-copilot`, `Capability profile: P0`, `Exception: none`. CI still checks that the changed paths are Routine. |
| **No AI used** | Light path with `AI use: none`, `AI tool: none`, `Capability profile: n/a`. |
| **The task is large** | `new-change` uses `change-splitter` and writes several increments. One increment is one pull request. If CI reports `review-budget`, type `/change-splitter specs/NNN-name/spec.md`. |
| **Generated files** (API clients, migrations from a tool) | List them in section 7 of the specification, row "Generated files", with the command that produces them. CI does not count their lines. The reviewer checks the generator. |
| **A finding must be accepted for a time** | Type `/exception-drafter <finding>`. The risk owner fills in "Approved by". Put `Exception: governance/exceptions/EXC-NNN-name.md` in the pull request. A weekly issue reminds you 14 days before the expiry date. |
| **A review finding should never come back** | Type `/rule-from-finding <finding>`. The skill writes a Semgrep rule with a test file. |
| **You pasted a key or personal data into the prompt** | Claude Code CLI blocks the prompt. In the IDE nothing blocks it: rotate the key, and tell the agent. The `sensitive-data-guard` skill stops it from spreading into files. |
| **Restricted change** | Do not use AI. Use the normal human process, or get an approved exception first. |

## 7. When a CI check fails

| Check | Typical message | What to do |
|---|---|---|
| Governance metadata | `Specification ... does not exist`, `status is not 'approved'`, `Increment ... is not in section 8` | Fix the `Specification:` or `Increment:` line, or approve the specification. |
| Change guardrails: `scope` | Changed files are not in section 7 or in the increment | Move the change to the right increment, or update the specification and get approval again. |
| Change guardrails: `risk-drift` | Declared class is lower than the class of the changed paths | Raise the risk class in the specification. The technical lead approves it. |
| Change guardrails: `review-budget` | N changed lines in M files, budget ... | Split the change (`/change-splitter`). Only the risk owner can accept it with an exception. |
| Change guardrails: `new-file-size` | New file above the limit | Split the file, or declare it as generated. |
| Change guardrails: agent configuration | Setting weaker than `agent-baseline.yaml` | Restore the setting. A planned change to the baseline needs code-owner review. |
| Secrets and personal data | Kind of finding, file and line. Never the value. | Delete the value from the change and from the history. Rotate a real key. Mark synthetic test data with `sensitive-data: synthetic`. |
| Dependencies and licences | Advisory ID, or licence not on the allowlist | Use a fixed version, or ask the legal or IP specialist. Record an exception if you accept it. |
| Tests and SAST | Test failure, or a Semgrep rule ID | Fix the code. Do not suppress the finding to pass. |

Items under "Requires human review" (deleted tests, new suppression markers, governance-file changes, generated files) do not fail the check. The reviewer must look at them.

## 8. Platform differences

| Feature | Claude Code CLI | Claude Code in VS Code | Copilot agent mode (VS Code) | Copilot cloud agent |
|---|---|---|---|---|
| Skills and read-only agents | Yes | Yes | Yes (reads `.claude/`) | `AGENTS.md`. Skills not tested. |
| Plan gate | Plan mode by default | Plan mode by default (test it: S21) | Planner agent and skill (advisory) | Works on a branch, opens a pull request |
| Prompt guard hook | Yes | No | No | No |
| Scope and size hook | Yes | No | No | No |
| Shell sandbox | Yes (macOS, Linux, WSL2) | Yes | Preview | Firewall on the Bash tool |
| CI checks and ruleset | Yes | Yes | Yes | Yes |

"Yes" means that the documentation describes the feature. Claim it as enforced only after a test on your versions ([TESTING.md](TESTING.md)). The CI checks are the same for every platform. They are the backstop for each control that a platform cannot enforce.

## 9. Update or uninstall

- **Update:** run the setup script again. It creates `.governance-new` files for each file that changed. Merge them.
- **Uninstall:** delete the folders and files in section 1, the two lines in `.gitignore`, and the ruleset in the repository settings.

## 10. Troubleshooting

| Problem | Cause and fix |
|---|---|
| Claude Code does not start: sandbox not available | `failIfUnavailable` is on. Install `bubblewrap` and `socat` (Linux, WSL2). On native Windows use WSL2. |
| `/new-change` is not offered in VS Code | Check that your VS Code and Copilot Chat versions support agent skills, and that the workspace is trusted. Open the project folder that contains `.claude/`. |
| Guardrails: `git diff ... failed` | CI needs the full history: `fetch-depth: 0` in the checkout step. Locally, check the base branch name (`main` or `master`). |
| Dependencies job fails with exit code 127 | OSV-Scanner could not reach the network. The job fails on purpose, so that it does not pass without a scan. Run it again. |
| A false positive in the sensitive-data scan | If the value is synthetic, add `sensitive-data: synthetic` on the same line. CI lists each new marker for the reviewer. |
| The ruleset cannot find a check | Run the workflow once on a pull request before you import the ruleset. |
