# Risk Classification Questions

Use these questions to propose a risk class. Each "yes" sets a minimum class. Propose the highest class that you found. A person approves the final class.

| # | Question | If yes, minimum class |
|---|---|---|
| 1 | Does any affected path match a pattern in `policy-config/risk-paths.yaml`? | The class of that pattern |
| 2 | Does the change modify business logic, a dependency, or behaviour that users can see? | Elevated |
| 3 | Does the change read, store, send or show personal data? | High impact |
| 4 | Does the change touch credentials, authentication, authorisation, cryptography, payments, infrastructure or a critical service? | High impact |
| 5 | Is the change hard to reverse (data migration, deletion, an external commitment)? | High impact |
| 6 | Does a law, a contract or the policy prohibit AI use for this work? | Restricted |
| 7 | Does the task need data above `max_data_class` for the tool? | Restricted |

If every answer is "no", the class is Routine.

## Reasons to write

Give one short reason for the proposed class. Name the question and the path or the data. Examples:

- "Elevated: changes refund logic in `sample-app/orders/store.py` (question 2, path rule `sample-app/orders/**`)."
- "High impact: the new endpoint returns customer e-mail addresses (question 3)."

## Capability profile

Propose the smallest profile that can do the task.

| Profile | Use when |
|---|---|
| P0 Suggest | The user writes the code. You only suggest. |
| P1 Edit | You change files. The user runs commands and tests. |
| P2 Execute | You also run tests or build commands. Network only to approved package sources. |
| P3 Connected | Network, external tools or MCP servers. Only when the user asks for it. It needs a separate approval. |

For a High impact change, prefer P1. The human runs the commands.
