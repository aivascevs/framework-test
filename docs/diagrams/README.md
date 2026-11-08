# Diagrams

| File | Shows | Used in |
|---|---|---|
| `01-framework-overview` | Two dimensions, core and extensions, assurance modes | FRAMEWORK.md §1 |
| `02-lifecycle` | Lifecycle of a governed change, with repository artefacts | FRAMEWORK.md §3 |
| `03-control-points` | Where each control acts, coloured by assurance mode | FRAMEWORK.md §5 |
| `04-c4-context` | C4 Level 1: system context | FRAMEWORK.md §6 |
| `05-c4-container` | C4 Level 2: containers | FRAMEWORK.md §6 |
| `06-c4-component-ci` | C4 Level 3: components of the CI workflow | FRAMEWORK.md §6 |
| `07-risk-capability` | Controls grow with risk and capability | FRAMEWORK.md §2, `governance/risk-and-capability.md` |
| `08-developer-flow` | Day-to-day flow: one command, three human gates, skills, agents and CI | FRAMEWORK.md §3.1, README |

The `.mmd` files are the sources. The `.svg` and `.png` files are rendered copies for documents and print.

The C4 views use C4 notation (person, system, container, component, external system, boundary) in Mermaid flowchart syntax. The Mermaid C4 syntax is experimental, and its layout overlapped labels in these views.

## Render the images

```bash
npm install -g @mermaid-js/mermaid-cli@12.0.0
for f in docs/diagrams/*.mmd; do
  mmdc -c docs/diagrams/mermaid-config.json -i "$f" -o "${f%.mmd}.svg" -b white
  mmdc -c docs/diagrams/mermaid-config.json -i "$f" -o "${f%.mmd}.png" -b white -s 2
done
python scripts/sync_readme_diagrams.py     # copy the sources into README.md and docs/*.md
```

`puppeteer.json` points mermaid-cli at a local Chromium. Add `-p docs/diagrams/puppeteer.json` if mermaid-cli cannot download its own browser.
