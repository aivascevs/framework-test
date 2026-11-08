# Third-Party Notices

## Included in this repository

| Component | Location | Source | Licence | Version |
|---|---|---|---|---|
| ASD-STE100 skill (SKILL.md, references, examples, ste-lint.py) | `.claude/skills/asd-ste100/` | https://github.com/danyuchn/asd-ste100-skill | MIT (`.claude/skills/asd-ste100/LICENSE`) | commit `8da6b6340aa2` |

The ASD-STE100 skill applies the structural rules of the ASD-STE100 standard. It does not include the official ASD-STE100 dictionary. The standard is available from ASD on request.

## Downloaded at run time (not included)

| Tool | Used for | Licence | Pinned version |
|---|---|---|---|
| gitleaks CLI | Secrets and personal data job | MIT | 8.30.1 |
| OSV-Scanner | Dependency vulnerabilities and licences | Apache-2.0 | 2.7.0 |
| Semgrep Community Edition | SAST with self-written rules | LGPL-2.1 (engine) | 1.180.0 |
| pytest and its dependencies | Sample application tests | MIT, Apache-2.0 OR BSD-2-Clause, BSD-2-Clause | see `sample-app/requirements.txt` |
| PyYAML | Script dependency | MIT | 6.0.3 |
| GitHub Actions: checkout, setup-python, upload-artifact | CI | MIT | pinned by commit SHA in the workflow |

Licences were checked against the upstream `LICENSE` files and the PyPI metadata on 2026-10-26.

## Queried at run time

| Service | Used by | Purpose |
|---|---|---|
| PyPI JSON API, npm registry, NuGet API | `dependency-check` skill (`check_package.py`) | Package exists, version, first release date, declared licence |
| OSV.dev API | `dependency-check` skill, OSV-Scanner | Known advisories |

The skill sends only the package name and version. It sends no code.

## Not used on purpose

- `gitleaks-action` v2 and later: commercial licence for organisation repositories. The workflow runs the MIT CLI instead.
- Semgrep registry rules: they have their own licence (Semgrep Rules License). The repository uses only self-written rules.
