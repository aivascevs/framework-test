# Governance Framework for Secure and Compliant AI-Assisted Code Generation

A governance framework for software teams that use AI coding assistants and AI agents, with a working reference implementation for **Claude Code** and **GitHub Copilot**.

AI tools write code faster than people can review it. The code can contain insecure patterns, secrets, personal data, invented or unlicensed dependencies, and changes outside the task. The framework decides, for each change, what the AI tool may do, under which conditions, who approves the result and which evidence the team keeps.

> This repository is the practical part of a master's thesis. Chapter 4 of the thesis describes the framework. Chapter 5 reports the evaluation from [`evaluation/`](evaluation/).

## How it works

The governed path is the easiest path. A developer types one command and makes three decisions. Skills, read-only agents and CI do the rest.

<!-- diagram:08-developer-flow -->
```mermaid
flowchart TB
    subgraph s1["1 · Start — Claude Code or GitHub Copilot in VS Code"]
        direction LR
        a1(["Developer types<br/><code>/new-change &lt;task&gt;</code>"]) --> a2["<b>new-change</b> skill<br/>max. 4 questions · proposes risk,<br/>data class, profile · writes SEC / DATA / LIC<br/><b>change-splitter</b>: increments within the review budget"]
        a2 --> g1{{"<b>Human gate 1</b><br/>approve the specification"}}
    end
    subgraph s2["2 · Plan and build — inside the agent"]
        direction LR
        b1["<b>governed-change</b> skill<br/>writes <code>.active-spec</code>"] --> b2["<b>planner</b> agent<br/>read-only"]
        b2 --> g2{{"<b>Human gate 2</b><br/>approve the plan<br/><i>Claude Code: plan mode</i>"}}
        g2 --> b3["Tests first, then code<br/><b>dependency-check</b> · <b>sensitive-data-guard</b><br/><i>CLI hooks: scope_guard, prompt_guard</i>"]
        b3 --> b4["<b>reviewer</b> agent<br/>read-only findings<br/>+ sensitive-data scan"]
    end
    subgraph s3["3 · Pull request and CI — automatic"]
        direction LR
        c0["PR body:<br/><code>Specification: specs/…/spec.md</code><br/><code>Increment: INC-n</code>"] --> c1["Metadata<br/>read from the spec"]
        c0 --> c2["Change guardrails<br/>scope · risk drift · size (C9) · agent config"]
        c0 --> c3["Secrets and<br/>personal data"]
        c0 --> c4["Dependencies<br/>and licences"]
        c0 --> c5["Tests and SAST"]
        c1 & c2 & c3 & c4 & c5 --> c6["Evidence summary<br/>review order · items for human review"]
    end
    subgraph s4["4 · Decide"]
        direction LR
        g3{{"<b>Human gate 3</b><br/>review and approve the PR<br/>highest risk first<br/>CODEOWNERS · ruleset"}} --> m1(["Merge"])
        x1["<b>exception-drafter</b><br/>risk owner approves"] -.-> g3
        x3["Weekly reminders<br/>exception expiry · tool review"] -.-> x1
        x2["<b>rule-from-finding</b><br/>finding → new Semgrep rule + test in CI"]
    end
    s1 --> s2
    s2 --> s3
    s3 --> s4

    classDef gate fill:#fff4d6,stroke:#b7791f,stroke-width:2px,color:#1a1a1a
    classDef agent fill:#e6f0ff,stroke:#2b6cb0,color:#1a1a1a
    classDef ci fill:#e6f6ec,stroke:#2f855a,color:#1a1a1a
    classDef side fill:#f4f4f5,stroke:#71717a,stroke-dasharray:4 3,color:#1a1a1a
    class g1,g2,g3 gate
    class a2,b1,b2,b3,b4 agent
    class c0,c1,c2,c3,c4,c5,c6 ci
    class x1,x2,x3 side
```

_Source: [`docs/diagrams/08-developer-flow.mmd`](docs/diagrams/08-developer-flow.mmd) · image: [SVG](docs/diagrams/08-developer-flow.svg), [PNG](docs/diagrams/08-developer-flow.png)_

The framework has:

- **Two assessments for each change:** a change risk class (Routine, Elevated, High impact, Restricted) and a tool capability profile (P0 Suggest to P3 Connected).
- **Nine core controls** (C1–C9) for every AI-assisted change.
- **Nine agentic extensions** (A1–A9). They apply only when the tool can act: edit files, run commands, use the network, reach credentials or external tools.
- **An honest assurance label** on every control: Enforced, Detected, Advisory or Manual. Nobody mistakes an instruction for a block.

## Documentation

| Read | When you want to |
|---|---|
| **This README** | Get the idea in five minutes |
| [**docs/FRAMEWORK.md**](docs/FRAMEWORK.md) | Understand the whole framework: principles, risk and capability, lifecycle, controls, assurance model, C4 architecture |
| [**docs/INSTALL-AND-USE.md**](docs/INSTALL-AND-USE.md) | Install it in a project and use it every day, on either platform |
| [**docs/TESTING.md**](docs/TESTING.md) | Test it on the sample application and see what is covered and what is not |
| [agent/README.md](agent/README.md) | Platform details: what Claude Code and Copilot can enforce |
| [governance/](governance/) | The normative texts: policy, risk classes, control catalogue, tool register |
| [LIMITATIONS.md](LIMITATIONS.md) | What no test in this repository can establish |
| [docs/thesis-alignment.md](docs/thesis-alignment.md) | How the thesis chapters map to the files here |

## Quick start

```bash
./setup.sh --check                         # check the prerequisites on this machine
./setup.sh /path/to/your/project           # install for Claude Code and GitHub Copilot
python evaluation/run_scenarios.py         # or: see the controls work on the sample application
```

On Windows, use `.\setup.ps1 -Target C:\path\to\project`. Then, in the agent chat of your project:

```text
/new-change add a count of refunded orders per customer
```

## What it is not

The framework does not add a new coding agent, a gateway or an audit service, and it does not give legal advice. A passed check does not prove that a change is secure, correct or compliant. Each result holds only for the tested versions and settings. Read [LIMITATIONS.md](LIMITATIONS.md) before you rely on a result.

## Licence

MIT ([LICENSE](LICENSE)). The [`asd-ste100`](.claude/skills/asd-ste100/) skill is a copy of [danyuchn/asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill) (MIT). The CI downloads gitleaks (MIT), OSV-Scanner (Apache-2.0) and Semgrep CE (LGPL-2.1) at run time. See [NOTICE.md](NOTICE.md).
