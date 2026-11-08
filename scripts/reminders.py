#!/usr/bin/env python3
"""C1, C8 — List governance items that are due or overdue.

Read by the weekly workflow .github/workflows/governance-reminders.yml, which
opens or updates one issue with the list. Nobody needs to run this by hand.

Items:
  - exception records in governance/exceptions/ that expire within the warning window, or expired
  - exception records with no approver (draft not approved)
  - [[IgnoredVulns]] ignoreUntil and [[PackageOverrides]] effectiveUntil in policy-config/osv-scanner.toml
  - the tool register review (governance/approved-tools.yaml, last_review + review interval)

Usage:
    reminders.py [--root .] [--today YYYY-MM-DD] [--days 14] [--out reminders.md]
Exit code: 0 always. The output file is empty when nothing is due.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path

import yaml

REVIEW_INTERVAL_DAYS = 183   # "Review at least every 6 months" (approved-tools.yaml)
DATE = r"(\d{4}-\d{2}-\d{2})"


def field(text: str, name: str) -> str:
    m = re.search(rf"^\|\s*{re.escape(name)}\s*\|\s*(.*?)\s*\|\s*$", text, re.M)
    return m.group(1) if m else ""


def due(label: str, date: dt.date, today: dt.date, days: int) -> str | None:
    left = (date - today).days
    if left < 0:
        return f"**Overdue** ({-left} days): {label} — {date}"
    if left <= days:
        return f"Due in {left} days: {label} — {date}"
    return None


def collect(root: Path, today: dt.date, days: int) -> list[str]:
    items: list[str] = []
    for path in sorted((root / "governance" / "exceptions").glob("EXC-*.md")):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root).as_posix()
        approver = field(text, "Approved by")
        if not approver or approver.startswith("<"):
            items.append(f"Not approved: `{rel}` has no risk owner in 'Approved by'.")
        m = re.fullmatch(DATE, field(text, "Expiry or review date"))
        if not m:
            items.append(f"No expiry date: `{rel}`.")
            continue
        hit = due(f"exception `{rel}` expires. Renew it with a new approval, or remove it and fix the finding",
                  dt.date.fromisoformat(m.group(1)), today, days)
        if hit:
            items.append(hit)

    osv = root / "policy-config" / "osv-scanner.toml"
    if osv.is_file():
        for block in re.split(r"(?=^\[\[)", osv.read_text(encoding="utf-8"), flags=re.M):
            m = re.search(rf"(ignoreUntil|effectiveUntil)\s*=\s*\"?{DATE}", block)
            if not m:
                continue
            name = re.search(r"^\s*(?:id|name)\s*=\s*\"([^\"]+)\"", block, re.M)
            label = f"`policy-config/osv-scanner.toml` entry {name.group(1) if name else '(no id)'} ({m.group(1)})"
            hit = due(label, dt.date.fromisoformat(m.group(2)), today, days)
            if hit:
                items.append(hit)

    register = root / "governance" / "approved-tools.yaml"
    data = yaml.safe_load(register.read_text()) or {}
    last = str(data.get("last_review", "")).strip()
    if re.fullmatch(DATE, last):
        hit = due("review of the tool register `governance/approved-tools.yaml` "
                  "(provider terms, data limits, modes, versions)",
                  dt.date.fromisoformat(last) + dt.timedelta(days=REVIEW_INTERVAL_DAYS), today, days)
        if hit:
            items.append(hit)
    else:
        items.append("`governance/approved-tools.yaml` has no valid `last_review` date.")
    return items


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--today")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    items = collect(Path(args.root), today, args.days)
    text = ""
    if items:
        text = "\n".join([f"Governance items due by {today + dt.timedelta(days=args.days)}:", ""]
                         + [f"- [ ] {i}" for i in items]
                         + ["", "This issue is updated every week by `.github/workflows/governance-reminders.yml`. "
                            "Close it when every item is done."]) + "\n"
    print(text or "Nothing is due.")
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
