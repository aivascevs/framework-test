# Governance Policy

Version 1.0. Owner: governance or security owner. Review: every 6 months, or when a tool, a capability or the evidence changes.

This policy states the rules for software changes that use AI coding assistants or AI agents. It applies to every change in this repository where AI suggests code, writes code or performs actions.

## 1. Scope

The policy has two parts:

- **Core controls (C1–C9)** apply to all AI-assisted changes. It does not matter if the tool only suggests code or if it performs actions.
- **Agentic extensions (A1–A9)** apply only when the tool has a capability in the task environment. Examples are file modification, command execution, network access, credential access and access to external tools. The capability that you give the tool starts the extension, not the product name.

The policy does not cover the development of foundation models. It does not give legal advice. It does not assess risks of AI features inside the product that you build.

## 2. Principles

1. **Govern the change, not the AI authorship.** Controls apply to the request, the specification, the context, the change, the verification and the approval. The repository record can show that AI was used. It cannot show which lines the model wrote.
2. **Apply controls that match the risk.** The review and verification effort must match the change risk and the tool capability. An assistant that only suggests code is not equal to an agent with a shell.
3. **Keep guidance separate from enforcement.** Policies, templates and instruction files describe the expected behaviour. They do not stop a person or a model from doing something else. When a rule must hold, use a platform permission, a repository rule or a required CI check.
4. **Give least privilege and bounded autonomy.** Give the tool only the data, commands, network access, credentials and external tools that the task needs. A human approves any change to these permissions and any significant action.
5. **Verify independently and keep proportionate evidence.** Tests and explanations that an agent writes are inputs to the review. They are not independent proof. Required checks run in a separate validation path and link to the change. Keep the evidence that explains the decision and the checks. Do not keep raw prompts by default.
6. **Make human accountability visible.** A named person is accountable for the classification, the approval, each exception and the release. Automation can block or flag a change. Automation cannot accept accountability or approve a change.
7. **Delegate only up to the reviewing capability.** One change from an AI tool must stay small enough that a qualified person can review all of it. The specification splits a large task into increments that a person can review. Automated checks and an AI reviewer reduce the review effort, but a human makes the decision. Each team sets its own budget (`policy-config/review-budget.yaml`).

### Why raw prompts are not kept by default

Prompt records can contain source code, personal data or other sensitive context. If your organisation needs more records, define their purpose, who can read them, how long you keep them and how you protect them. Record this decision in this policy.

## 3. Roles

| Role | Accountable for |
|---|---|
| Governance or security owner | This policy, the tool register (`approved-tools.yaml`), the risk classes, the capability profiles and the exception process |
| Change author or agent operator | The specification, the risk class proposal, the AI-use declaration, the capability profile for the task and the change itself |
| Technical lead | Approves the risk class for Elevated changes and above |
| Reviewer or code owner | The review decision. Checks the change against the specification. Records licence and exception decisions. |
| Dependency or security owner | Dependency findings and escalation of unclear code origin |
| Legal or IP specialist | Licence and IP questions that the reviewer escalates |
| Service owner | Operation, incidents and the feedback into this policy |

A person who prepares a change with an agent cannot be the only approver of that change. An agent never approves a change.

## 4. Rules

1. Use only the tools and modes in `governance/approved-tools.yaml`. Send to a tool only the data classes that the register permits.
2. Start every AI-assisted change from a specification (`specs/_template/spec.md`). Record the risk class and the permitted capabilities before the AI starts work.
3. Do not give the tool secrets, credentials or data above the permitted data class (`governance/data-handling.md`).
4. Open a pull request with the completed template. Declare the AI use.
5. Keep each pull request inside the change budget for its risk class (C9). Split a larger change into increments in section 8 of the specification. One increment is one pull request.
6. Let the required CI checks run. Do not merge a change with a failed required check unless an approved exception covers it.
7. Get the approval of a human reviewer who did not prepare the change. High impact changes need a reviewer with the right expertise.
8. Record every exception with the template `governance/exception-template.md`. Each exception has an owner, a scope and an expiry date.
9. Report incidents that involve AI-assisted changes. Use the lessons to update this policy, the templates and the checks.

## 5. Restricted changes

Do not delegate a Restricted change to an AI tool. Use the normal human process. The only alternative is an approved exception from the governance owner (`governance/exception-template.md`).

## 6. Related documents

- [Risk classes and capability profiles](risk-and-capability.md)
- [Controls and assurance modes](controls.md)
- [Data handling](data-handling.md)
- [Approved tools register](approved-tools.yaml)
- [Exception template](exception-template.md)
