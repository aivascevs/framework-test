# Agent Extension: Claude Code and GitHub Copilot

This folder documents the agentic extension (A1–A9) for two platforms. The platforms are Claude Code (CLI and VS Code extension) and GitHub Copilot (VS Code agent mode and the Copilot cloud agent). The live configuration files sit where each platform reads them. One copy of the skills and agents serves both platforms.

To install the framework into a project, run the setup script (section 6). Developers do not run any other script by hand.

## 1. Files

| File | Platform | Purpose | Mode |
|---|---|---|---|
| [`AGENTS.md`](../AGENTS.md) | Both | Baseline instructions | Advisory |
| [`CLAUDE.md`](../CLAUDE.md) | Claude Code | Imports `AGENTS.md` | Advisory |
| [`.claude/skills/`](../.claude/skills) | Both | Eight skills (section 2) | Advisory. The bundled scanners detect. |
| [`.claude/agents/`](../.claude/agents) | Both | Two read-only agents: `planner` (with size estimates), `reviewer` (with a review order) | Read-only tool list: enforced if tested |
| [`.claude/settings.json`](../.claude/settings.json) | Claude Code | Plan mode by default, permission rules, Bash sandbox, hooks | Enforced for the tested tool paths |
| [`.claude/hooks/`](../.claude/hooks) | Claude Code CLI | `prompt_guard.py`, `scope_guard.py` | Enforced in the CLI if tested. Not in VS Code. |
| [`profiles/claude-code-P1-edit.json`](profiles/claude-code-P1-edit.json) | Claude Code | Profile P1: no shell, no web | Enforced if tested |
| [`profiles/claude-code-P2-execute.json`](profiles/claude-code-P2-execute.json) | Claude Code | Profile P2: strict network allowlist | Enforced if tested |
| [`.vscode/settings.json`](../.vscode/settings.json) | Copilot in VS Code | Agent sandbox (preview) and terminal approval rules | Enforced if tested. Approval rules ask. They do not block. |
| [`policy-config/agent-baseline.yaml`](../policy-config/agent-baseline.yaml) | CI | Minimum agent settings. CI fails a change that weakens them. | Detected |
| Repository settings, Copilot, Internet access | Copilot cloud agent | Firewall for the agent's Bash tool | Enforced if tested |

## 2. Skills and agents

| Name | Type | Starts when | What it does | Controls |
|---|---|---|---|---|
| `new-change` | Skill | The developer types `/new-change <task>` or describes a new task | Asks at most four questions. Proposes the risk class, data class and profile with reasons (`policy-config/risk-paths.yaml`). Writes acceptance criteria and SEC, DATA and LIC requirements. Writes a draft specification. | C2, C3, C5, C6 |
| `governed-change` | Skill | The specification is approved | Writes `.active-spec`. Calls the planner. Writes tests first. Implements. Calls the reviewer. Runs the sensitive-data scan. Writes the pull request text. | C2, C4, C7, A1, A8 |
| `planner` | Agent (Read, Grep, Glob) | Called by `governed-change` | Returns a plan in the `plan.md` format. Cannot edit. | A8 |
| `reviewer` | Agent (Read, Grep, Glob) | Called by `governed-change` | Compares the change with the specification. Returns findings. Cannot edit or approve. | C4, C6 |
| `sensitive-data-guard` | Skill + scanner | Secrets or personal data may be present. Before a commit. | Stops sensitive data from spreading. The scanner prints the kind and location, never the value. | C3, A4 |
| `dependency-check` | Skill + checker | Before a new package is proposed or installed | Checks that the package and version exist (invented names), age, licence and known advisories. | C5 |
| `change-splitter` | Skill | The estimate is above the review budget, CI reports `review-budget`, or `/change-splitter` | Splits the work into increments (one pull request each) with rules for reviewable slices. | C9 |
| `rule-from-finding` | Skill | `/rule-from-finding` after a review finding | Writes a Semgrep rule with a test file. | C4, C8 |
| `exception-drafter` | Skill | `/exception-drafter` when a team accepts a risk | Drafts an exception record. The risk owner approves it. | C8 |
| `asd-ste100` | Skill | Specifications and pull request text | Plain-language rewrite | C6 |

Both platforms read `.claude/skills/` and `.claude/agents/`. VS Code reads the Claude agent format and maps the tool names. Test this on your VS Code version (scenario S21).

## 3. The plan gate on each platform

The developer approves the specification and the plan before the agent changes a file.

| Step | Claude Code | GitHub Copilot in VS Code |
|---|---|---|
| Start | `/new-change <task>` | `/new-change <task>` in agent mode |
| Plan gate | `permissions.defaultMode: "plan"`. The session starts in plan mode. The agent cannot edit until the developer accepts the plan. | No repository setting for a default plan mode. The `planner` agent is read-only. The `governed-change` skill stops after the plan. Advisory: test it (S21). |
| Edit gate | Permission rules. `scope_guard.py` hook in the CLI. | Built-in edit approval. Terminal approval rules. |
| Final gate | CI and a human approval in the pull request | Same |

## 4. What each platform can enforce

The capability triggers come from [governance/risk-and-capability.md](../governance/risk-and-capability.md). "Enforced" means that the documentation describes a technical limit. Claim it only after you test it on the recorded version, operating system and settings.

| Control | Claude Code | GitHub Copilot (VS Code agent mode) | Copilot cloud agent |
|---|---|---|---|
| A1 Write only in the workspace and the scope | Bash sandbox: OS-level write limit. Protected paths include `.claude/`, `.vscode/`, `.git/hooks`. Edit and Write tools: `ask` rules on governance paths. CLI: `scope_guard.py` blocks edits outside section 7 of the active specification. CI: scope check. | Agent sandbox (preview) for terminal commands. Built-in edit tools use their own approval. CI: scope check. | Runs on a branch. CI scope check and branch protection apply. |
| A2 Limit commands | `deny`, `ask` and `allow` rules. Deny rules can miss a program inside `sh -c` or called by path. | `chat.tools.terminal.autoApprove`. A `false` rule asks for approval. It does not block. | Not configurable per command. |
| A3 Network allowlist | Sandbox proxy with `allowedDomains` (package registries and OSV.dev). `strictAllowlist` (P2 profile) denies other hosts without a prompt. No TLS inspection. | `chat.agent.sandbox.network.*` (preview). | Firewall with a recommended allowlist. Covers the agent's Bash tool only. |
| A4 No credentials, no sensitive prompts | `sandbox.credentials`. `Read` deny rules. CLI: `prompt_guard.py` blocks a prompt with a secret or personal data. | `deniedPaths` in the sandbox. Prompt input: Manual (training, `sensitive-data-guard` skill). | Scoped token. Do not add secrets to the Copilot environment. |
| A5 MCP | `enableAllProjectMcpServers: false`. No `.mcp.json` (CI fails if it appears). | No `.vscode/mcp.json` (CI fails if it appears). | No MCP configuration. |
| A6 Untrusted content | Advisory (`AGENTS.md`). Containment through A1–A3. | Same | Same |
| A7 Configuration integrity | `CODEOWNERS`, ruleset, `check_agent_config.py` in CI | Same | Same |
| A8 Monitor and stop | Plan mode by default. Read-only planner. | Read-only planner. Skill stops after the plan. | Works on its own branch. Opens a pull request. |
| A9 No push, merge or deploy | `Bash(git push *)` deny rule + ruleset without bypass | Approval rule + ruleset | Cannot merge. The ruleset requires a human approval. |

## 5. Hooks: CLI only

Claude Code runs the hooks in `.claude/settings.json` in the CLI. Issue reports say that the VS Code extension does not run `UserPromptSubmit` and `PreToolUse` hooks reliably. GitHub Copilot does not read `.claude/settings.json`. For this reason:

- the hooks are an extra layer for CLI users, not the main control
- every hook decision is checked again in CI (scope: `check_guardrails.py`. Sensitive data: the "Secrets and personal data" job.)
- a hook that fails to start permits the action. The hook must not stop the developer because of its own error. CI is the backstop.

Most developers prompt in the IDE chat. For them, protection of the prompt input stays Manual (C3). The `sensitive-data-guard` skill limits how far data spreads after the agent sees it.

## 6. Set up

The full installation and daily-use guide is [docs/INSTALL-AND-USE.md](../docs/INSTALL-AND-USE.md). This section lists the platform-specific points.

Run the setup script from this repository. It copies the framework into a target project, checks prerequisites for both platforms and prints the next steps. It does not change user or managed settings.

```bash
./setup.sh /path/to/project                       # macOS, Linux, WSL2
./setup.sh /path/to/project --platform claude      # only Claude Code files
./setup.sh /path/to/project --platform copilot     # only Copilot files
./setup.sh --check                                 # only check prerequisites here
```

```powershell
.\setup.ps1 -Target C:\src\project                # Windows (Copilot; Claude Code needs WSL2 for the sandbox)
.\setup.ps1 -Target C:\src\project -Platform copilot
.\setup.ps1 -Check
```

The script never overwrites a file. When a file exists, it writes `<name>.governance-new` next to it and lists it, so a person merges the two.

### Claude Code

1. Use macOS, Linux or WSL2. Native Windows has no sandbox.
2. On Linux and WSL2, install `bubblewrap` and `socat`. Run `/sandbox` in Claude Code to check.
3. For profile P1 or P2, start with the profile file:

   ```bash
   claude --settings agent/profiles/claude-code-P1-edit.json
   claude --settings agent/profiles/claude-code-P2-execute.json
   ```

4. Record the version (`claude --version`), the operating system and the profile in the evaluation results.

`failIfUnavailable: true` stops Claude Code from starting when the sandbox cannot run. A developer can override project settings in local or user settings. Only managed settings hold against the developer.

### GitHub Copilot

1. **VS Code agent mode:** open the project in VS Code. The workspace settings turn on the agent sandbox (preview) and the terminal approval rules. On Linux and WSL2 the sandbox needs `bubblewrap`, `slirp4netns`, `util-linux` and `iptables`.
2. **Copilot cloud agent:** in the repository Settings, open Copilot, then Internet access. Keep the firewall on and the recommended allowlist. Add no custom hosts.
3. Use an organisation licence (Business or Enterprise). Do not use personal accounts (C1).
4. **Organisation settings (only with Business or Enterprise). The script does not set them:**
   - Content exclusion: exclude `**/.env*`, `**/secrets/**` and `**/*.pem` from Copilot.
   - Suggestions matching public code: Blocked (C5).
   - Policies: allow only the approved models and features in `governance/approved-tools.yaml`.
5. Record the VS Code version, the Copilot extension version and the settings in the evaluation results.

Workspace settings are advisory for the developer. To require the sandbox for everyone, use managed settings.

## 7. What to test

Run scenarios S12–S14, S20–S23 and S27 from [evaluation/protocol.md](../evaluation/protocol.md) on each platform. Use a disposable clone. Use only harmless file names and the host `example.com`. Report each result as Blocked, Detected, Requires human review or Not covered. A result holds only for that version, operating system and configuration.
