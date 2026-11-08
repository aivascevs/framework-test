#!/usr/bin/env python3
"""Insert the Mermaid sources from docs/diagrams/*.mmd into the documentation.

Files: README.md and docs/*.md. A marker line `<!-- diagram:NAME -->` is
followed by the diagram block and an image link, with paths relative to the
file. Run this script after you change a diagram, so the documents and the
diagram files stay the same. `--check` exits with 1 when a document is out of date.
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIAGRAMS = ROOT / "docs" / "diagrams"
BLOCK = re.compile(r"(<!-- diagram:(?P<name>[\w-]+) -->)\n(?:```mermaid\n.*?\n```\n\n_Source: .*?_\n)?", re.S)


def documents() -> list[Path]:
    return [ROOT / "README.md"] + sorted((ROOT / "docs").glob("*.md"))


def render_for(doc: Path):
    rel = Path(os.path.relpath(DIAGRAMS, doc.parent)).as_posix()

    def render(match: re.Match) -> str:
        name = match.group("name")
        src = (DIAGRAMS / f"{name}.mmd").read_text().strip()
        return (f"{match.group(1)}\n```mermaid\n{src}\n```\n\n"
                f"_Source: [`docs/diagrams/{name}.mmd`]({rel}/{name}.mmd) · "
                f"image: [SVG]({rel}/{name}.svg), [PNG]({rel}/{name}.png)_\n")
    return render


def main() -> int:
    stale = []
    for doc in documents():
        text = doc.read_text()
        new = BLOCK.sub(render_for(doc), text)
        if new != text:
            stale.append(doc.relative_to(ROOT).as_posix())
            if "--check" not in sys.argv:
                doc.write_text(new)
    if "--check" in sys.argv:
        if stale:
            print("Diagrams are out of date in: " + ", ".join(stale) + ". Run scripts/sync_readme_diagrams.py.")
            return 1
        print("Diagrams in the documentation are up to date.")
        return 0
    print("Updated: " + (", ".join(stale) or "nothing"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
