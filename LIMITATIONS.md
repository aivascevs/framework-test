# Limitations

This repository is a reference implementation of selected controls. It shows how the controls can be configured and what they do in defined test scenarios. It does not prove that the framework improves outcomes in an organisation.

## What no test in this repository can establish

- **Complete detection.** Scanners find only the secrets, insecure patterns and vulnerabilities that their rules and databases cover. A clean scan does not mean that no defect exists.
- **Legal compliance.** The licence check reads declared licence metadata. It does not decide if a licence is acceptable for your use. It cannot decide if generated code infringes a copyright.
- **Authorship provenance.** The AI-use declaration is self-reported. Nothing in the repository can show which lines a model wrote.
- **Review quality.** The host records that an approval happened. It cannot record how carefully the reviewer read the change.
- **Resistance to adaptive attacks.** The scenarios use benign, synthetic inputs. They do not test a determined attacker or a hostile package.
- **Production effectiveness.** The scenarios run on a sample application. Results do not transfer automatically to other systems or organisations.

## Enforcement depends on configuration

- **Instruction files are advisory.** `AGENTS.md`, `CLAUDE.md` and skills change what the model is likely to do. They do not stop a contrary action.
- **Agent sandboxes cover some tool paths only.** The Claude Code sandbox covers Bash commands and their child processes. Its Read, Edit and Write tools use permission rules instead. Local MCP servers and hooks run outside the sandbox. The VS Code agent sandbox is preview, and it does not cover built-in tools that do not start a process.
- **Hostname allowlists do not inspect TLS.** A broad allowed domain can carry data out.
- **Workspace settings can be changed.** A developer can edit `.claude/settings.json` or `.vscode/settings.json`, or override them in local or user settings. Only managed settings from an administrator hold against the developer.
- **CI checks detect. The host blocks.** A failed check stops a merge only when the ruleset marks it as required and nobody can bypass the ruleset.
- **Hooks run in the Claude Code CLI only.** The VS Code extension and GitHub Copilot do not run `prompt_guard.py` and `scope_guard.py`. A hook that cannot start permits the action. CI checks the scope and the added lines again, but nothing checks a prompt typed in the IDE chat.
- **Prompt input is not protected in the IDE.** Most developers prompt in the IDE. There, protection of the prompt (C3) stays Manual. The `sensitive-data-guard` skill only limits how far data spreads after the model sees it.
- **The plan gate differs by platform.** Claude Code starts in plan mode (`defaultMode: plan`). GitHub Copilot has no repository setting for this. There the gate is the read-only planner and the skill instruction, which are advisory.
- **Separation of duties needs two people.** A single-account demonstrator cannot show that the author and the reviewer are different people.

## Limits of the automated checks

- **Risk classification by path is a heuristic.** `policy-config/risk-paths.yaml` gives a minimum class from file paths. A risky change in an unlisted path stays Routine for the check. A person sets the final class.
- **The scope check compares file names, not intent.** A file inside section 7 can still get a change that the specification does not describe. The reviewer checks the content.
- **Test and suppression flags are counts and patterns.** A weakened assertion, or a suppression in an unknown syntax, is not flagged.
- **The agent-configuration check reads the repository files only.** User, local and managed settings on a developer machine can differ.
- **The personal-data patterns find formats, not meaning.** Names, addresses and free text need human judgement. A reserved test domain or a `sensitive-data: synthetic` marker skips a line. CI reports every new marker to the reviewer.
- **The dependency checker needs the registries and OSV.dev.** Without network access it reports that it did not check advisories. CI checks them again.
- **The change budget counts lines, not effort.** 400 lines of a dense algorithm need more review than 400 lines of simple configuration. The budget in `policy-config/review-budget.yaml` is a team setting, not a measured limit. Code squeezed onto fewer lines, or moved into excluded or generated paths, passes the count. The reviewer and the scope check cover part of this.
- **The review order is a ranking, not a review.** It sorts files by path risk and size. It does not know which change in a file is risky. The reviewer agent's order is advice.
- **Increments depend on the split.** The `change-splitter` skill proposes increments, and the change author approves them. A bad split can still produce increments that are hard to review on their own.
- **Reminders need a person to act.** The weekly issue lists expiring exceptions. It does not remove them.

## Tools and versions

Results apply only to the tool versions, operating system, settings and date that the evaluation records in `evaluation/results/`. Re-test after any upgrade.
