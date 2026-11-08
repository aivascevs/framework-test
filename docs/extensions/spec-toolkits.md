# Mapping to Specification Toolkits (optional)

The core repository uses its own Markdown templates (`specs/_template/`). They need no installation and no telemetry, and they put the risk class and the capability profile first. Teams that already use GitHub Spec Kit or OpenSpec can keep their toolkit. Add the fields below so that the governance check can still read them.

| Framework field | Spec Kit (`specs/<feature>/`) | OpenSpec (`openspec/changes/<id>/`) |
|---|---|---|
| Purpose | `spec.md`, overview | `proposal.md`, "Why" |
| Acceptance criteria (AC) | `spec.md`, acceptance scenarios | spec deltas, scenarios |
| SEC, DATA, LIC requirements | add a section to `spec.md` | add a section to `proposal.md` |
| Risk class, data class | not present. Add front matter to `spec.md`. | not present. Add front matter to `proposal.md`. |
| AI use, tool, capability profile | not present. Add front matter. | not present. Add front matter. |
| Plan reviewed before execution | `plan.md` and `tasks.md` | `tasks.md` |

## Notes

- Neither toolkit enforces anything at merge. Their quality checks are prompts that an agent runs. The CI check in this repository still applies.
- The OpenSpec README states that it collects anonymous usage statistics. Disable or disclose this if you use it, because of the data-minimisation rule (C3).
- Point `scripts/check_metadata.py` at the toolkit's file by putting its path in the `Specification:` field of the pull request. The script reads YAML front matter from any Markdown file.
