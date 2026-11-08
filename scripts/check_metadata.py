#!/usr/bin/env python3
"""C2 / C7 — Check the governance metadata of a pull request.

The pull request body needs one line: "Specification: <path>". An optional
"Increment: INC-n" line names the increment (C9). An optional
"Exception: <path>" line links an exception record. CI reads the risk class,
AI use, AI tool, capability profile and data class from the specification, so
nobody types them twice. If the body repeats a value, it must match the
specification.

Light path: "Specification: none" is allowed for a Routine change where AI only
suggests code or is not used. Then the body must state "Risk class: Routine" and
"AI use: none" or "AI use: suggest" (with "AI tool" and "Capability profile: P0").

The script checks that values are present and consistent. It cannot check that
they are correct: that stays a human task (assurance mode: Detected).

Usage:
    check_metadata.py --event "$GITHUB_EVENT_PATH"      # in GitHub Actions
    check_metadata.py --body-file pr_body.md            # local test
    check_metadata.py ... --json-out metadata.json      # also write the resolved values
    check_metadata.py ... --report-only                 # always exit 0 (evidence job)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_lib import RISK_CLASSES, increments, read_spec  # noqa: E402

AI_USES = ["none", "suggest", "edit", "execute", "connected"]
PROFILE_FOR_USE = {"suggest": "P0", "edit": "P1", "execute": "P2", "connected": "P3"}
DATA_CLASSES = ["public", "internal", "confidential", "personal", "secret"]
FIELDS = ["Specification", "Increment", "Risk class", "AI use", "AI tool", "Capability profile", "Exception"]
SPEC_KEYS = {"Risk class": "risk_class", "AI use": "ai_use", "AI tool": "ai_tool",
             "Capability profile": "capability_profile"}
PLACEHOLDER = re.compile(r"<[^>]+>|\bNNN\b")


def parse_body(body: str) -> dict:
    """Return {field: value} for 'Field: value' lines. HTML comments are ignored."""
    body = re.sub(r"<!--.*?-->", "", body or "", flags=re.S)
    values = {}
    for field in FIELDS:
        m = re.search(rf"^\s*[-*]?\s*\**{re.escape(field)}\**\s*:\s*\**\s*(.+?)\s*$", body, re.M | re.I)
        if m:
            values[field] = m.group(1).strip().strip("`")
    return values


def exception_expiry(text: str) -> dt.date | None:
    m = re.search(r"Expiry or review date\s*\|\s*(\d{4}-\d{2}-\d{2})", text)
    return dt.date.fromisoformat(m.group(1)) if m else None


def check_exception(value: str, root: Path, today: dt.date, problems: list[str]) -> Path | None:
    if value.lower() == "none":
        return None
    path = root / value
    if not path.is_file():
        problems.append(f"Exception record '{value}' does not exist.")
        return None
    expiry = exception_expiry(path.read_text(encoding="utf-8"))
    if expiry is None:
        problems.append(f"Exception record '{value}' has no expiry date.")
        return None
    if expiry < today:
        problems.append(f"Exception record '{value}' expired on {expiry}.")
        return None
    return path


def check_tool(use: str, tool: str, profile: str, tools: dict, problems: list[str]) -> None:
    if use == "none":
        if tool not in ("none", ""):
            problems.append("AI use is 'none', so AI tool must be 'none'.")
        if profile.lower() not in ("n/a", "none", ""):
            problems.append("AI use is 'none', so Capability profile must be 'n/a'.")
        return
    if tool not in tools:
        problems.append(f"AI tool '{tool}' is not in governance/approved-tools.yaml "
                        f"(approved: {', '.join(tools) or 'none'}).")
    elif use not in tools[tool].get("modes_permitted", []):
        problems.append(f"AI use '{use}' is not a permitted mode for '{tool}' "
                        f"(permitted: {', '.join(tools[tool].get('modes_permitted', []))}).")
    expected = PROFILE_FOR_USE[use]
    if profile != expected:
        problems.append(f"Capability profile '{profile}' does not match AI use '{use}' (expected {expected}).")


def check(values: dict, root: Path, today: dt.date) -> tuple[list[str], dict]:
    """Return (problems, resolved values)."""
    problems: list[str] = []
    resolved = {f: values.get(f, "") for f in FIELDS}
    resolved["Exception"] = values.get("Exception", "none") or "none"
    resolved["Source"] = "pull request"

    spec_value = values.get("Specification", "")
    if not spec_value:
        problems.append("Line 'Specification: <path>' is missing from the pull request body "
                        "(use 'Specification: none' only for the light path).")
        return problems, resolved

    register = yaml.safe_load((root / "governance" / "approved-tools.yaml").read_text()) or {}
    tools = {t["id"]: t for t in register.get("tools", [])}
    exc_path = check_exception(resolved["Exception"], root, today, problems)

    # ---------------------------------------------------------- light path
    if spec_value.lower() == "none":
        risk = values.get("Risk class", "")
        use = values.get("AI use", "").lower()
        if risk != "Routine":
            problems.append("'Specification: none' is allowed only with 'Risk class: Routine'.")
        if use not in ("none", "suggest"):
            problems.append("'Specification: none' is allowed only with 'AI use: none' or 'AI use: suggest'. "
                            "Start the change with /new-change to write a specification.")
            return problems, resolved
        check_tool(use, values.get("AI tool", "").lower(), values.get("Capability profile", ""), tools, problems)
        resolved.update({"Risk class": risk, "AI use": use, "Data class": "(not declared)"})
        return problems, resolved

    # ---------------------------------------------------------- specification
    spec = root / spec_value
    if not spec.is_file():
        problems.append(f"Specification '{spec_value}' does not exist in the repository.")
        return problems, resolved
    meta, text = read_spec(spec)
    if meta is None:
        problems.append(f"Specification '{spec_value}' has no front matter (--- ... ---).")
        return problems, resolved
    if meta.get("__invalid__"):
        problems.append(f"Specification '{spec_value}' has front matter that is not valid YAML.")
        return problems, resolved

    resolved["Source"] = "specification"
    for field, key in SPEC_KEYS.items():
        resolved[field] = str(meta.get(key, "")).strip()
        if field in values and values[field].lower() != resolved[field].lower():
            problems.append(f"{field} in the pull request ('{values[field]}') differs from the specification "
                            f"('{resolved[field]}'). Remove the line or correct it.")
    resolved["Data class"] = str(meta.get("data_class", "")).strip()

    for key in ("id", "title", "owner", "risk_class", "data_class", "ai_use", "ai_tool",
                "capability_profile", "status"):
        value = str(meta.get(key, "")).strip()
        if not value or PLACEHOLDER.search(value):
            problems.append(f"Specification field '{key}' is empty or still a template value.")
    if str(meta.get("status", "")).lower() != "approved":
        problems.append("Specification status is not 'approved'. A person approves the specification.")

    risk, use = resolved["Risk class"], resolved["AI use"].lower()
    tool, profile = resolved["AI tool"].lower(), resolved["Capability profile"]
    if risk not in RISK_CLASSES:
        problems.append(f"Risk class '{risk}' is not one of: {', '.join(RISK_CLASSES)}.")
    if use not in AI_USES:
        problems.append(f"AI use '{use}' is not one of: {', '.join(AI_USES)}.")
        return problems, resolved
    check_tool(use, tool, profile, tools, problems)

    if risk == "Restricted" and use != "none" and exc_path is None:
        problems.append("Risk class 'Restricted' does not permit AI use without an approved exception record.")
    if risk in RISK_CLASSES[1:] and not str(meta.get("risk_confirmed_by") or "").strip():
        problems.append(f"Risk class '{risk}' needs 'risk_confirmed_by' (technical lead) in the specification.")
    data_class = resolved["Data class"].lower()
    if data_class not in DATA_CLASSES:
        problems.append(f"Specification data_class '{data_class}' is not one of: {', '.join(DATA_CLASSES)}.")
    elif use != "none" and tool in tools:
        limit = str(tools[tool].get("max_data_class", "public")).lower()
        if DATA_CLASSES.index(data_class) > DATA_CLASSES.index(limit) and exc_path is None:
            problems.append(f"Data class '{data_class}' is above the limit for '{tool}' ('{limit}').")
    incs = increments(text)
    inc = values.get("Increment", "").strip().upper()
    if inc and inc not in incs:
        problems.append(f"Increment '{inc}' is not in section 8 of the specification "
                        f"(found: {', '.join(incs) or 'none'}).")
    criteria = [line for line in re.findall(r"^\s*-\s*\*\*AC\d+\*\*\s*[—:-]\s*(.+)$", text, re.M)
                if not PLACEHOLDER.search(line)]
    if not criteria:
        problems.append("Specification has no completed acceptance criteria (lines like '- **AC1** — ...').")
    return problems, resolved


def load_body(args) -> str:
    if args.body_file:
        return Path(args.body_file).read_text(encoding="utf-8")
    event_path = args.event or os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        sys.exit("Give --event or --body-file.")
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    return (event.get("pull_request") or {}).get("body") or ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--event", help="path to the GitHub event JSON")
    ap.add_argument("--body-file", help="path to a file with the pull request body")
    ap.add_argument("--root", default=".", help="repository root")
    ap.add_argument("--today", help="date for expiry checks (YYYY-MM-DD); default: today")
    ap.add_argument("--json-out", help="write the resolved values and problems to this file")
    ap.add_argument("--report-only", action="store_true", help="always exit 0")
    args = ap.parse_args(argv)

    values = parse_body(load_body(args))
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    problems, resolved = check(values, Path(args.root), today)

    lines = ["### Governance metadata (C2, C7)", "", f"Values from: {resolved['Source']}", ""]
    lines += [f"- **{f}:** {resolved.get(f) or '(missing)'}" for f in FIELDS + ["Data class"] if f in resolved]
    lines.append("")
    lines += ([f"FAIL — {len(problems)} problem(s):"] + [f"- {p}" for p in problems]) if problems \
        else ["PASS — metadata is present and consistent."]
    report = "\n".join(lines)
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(report + "\n")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps({"values": resolved, "problems": problems}, indent=2))
    return 0 if args.report_only or not problems else 1


if __name__ == "__main__":
    sys.exit(main())
