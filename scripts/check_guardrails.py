#!/usr/bin/env python3
"""Change guardrails for a pull request (C2, C4, C9, A1, A7). Assurance mode: Detected.

Blocking findings (the check fails unless a valid exception record covers them):
  scope          a changed file is not in section 7 of the specification ("Files the agent may change"),
                 or not in the files of the declared increment (section 8)
  risk-drift     the declared risk class is lower than the minimum class of a changed path
                 (policy-config/risk-paths.yaml)
  review-budget  more changed lines or files than the budget for the risk class (C9,
                 policy-config/review-budget.yaml)
  new-file-size  a new file is larger than max_new_file_lines and is not declared as generated

Review findings (the check passes; the reviewer and the evidence summary see them):
  tests-removed       test files deleted, or more test functions removed than added
  suppression-added   new nosemgrep, gitleaks:allow, sensitive-data: synthetic, skip or noqa markers
  governance-change   changes to rules, checks, agent instructions or agent settings
  generated-files     files declared as generated: check the generator and its input
  increment-missing   the specification has more than one increment, but the pull request names none

The result also has a size summary and a suggested review order (highest risk first).

Usage:
    check_guardrails.py --event "$GITHUB_EVENT_PATH" --base BASE_SHA --head HEAD_SHA      # CI
    check_guardrails.py --body-file body.md --base main --head HEAD [--json-out f] [--report-only]
    check_guardrails.py --spec specs/NNN-x/spec.md [--increment INC-2] --base main --worktree  # agent, before the PR
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_metadata as cm  # noqa: E402
from spec_lib import (RISK_CLASSES, changed_files, class_rank, generated_files, git,  # noqa: E402
                      increments, load_budget, load_risk_paths, matches, minimum_class, numstat,
                      permitted_files, read_spec)

ALWAYS_PERMITTED = ["specs/{spec_dir}/**", "governance/exceptions/**"]
NOT_RISK_RATED = ["specs/**", "governance/exceptions/**"]
TEST_PATHS = ["**/tests/**", "**/test_*.py", "**/*_test.py", "**/*.test.*", "**/*.spec.*", "**/*Tests.cs"]
TEST_DEF = re.compile(r"^\s*(?:async\s+)?def\s+test_\w+|^\s*(?:it|test)\(\s*['\"]|\[(?:Fact|Test|TestMethod|Theory)\]")
SUPPRESSIONS = re.compile(
    r"nosemgrep|gitleaks:allow|sensitive-data:\s*synthetic|pytest\.mark\.(?:skip|xfail)|pytest\.skip\(|"
    r"#\s*noqa|eslint-disable|\[Ignore\]|\[Skip|\.skip\(", re.I)
GOVERNANCE_PATHS = ["governance/**", "policy-config/**", "scripts/**", ".github/**", ".claude/**",
                    ".vscode/**", "agent/**", "AGENTS.md", "CLAUDE.md"]


def diff_lines(base: str, head: str | None, cwd: Path) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """(added, removed) lines as (file, text). head None compares base with the working tree."""
    rng = [f"{base}...{head}"] if head else [base]
    out = git("diff", "--unified=0", "--no-color", "--no-renames", *rng, cwd=cwd)
    added, removed, old, new = [], [], None, None
    for raw in out.splitlines():
        if raw.startswith("diff --git "):
            old = new = None
        elif raw.startswith("--- "):
            old = raw[6:] if raw.startswith("--- a/") else None
        elif raw.startswith("+++ "):
            new = raw[6:] if raw.startswith("+++ b/") else None
        elif raw.startswith("+") and new:
            added.append((new, raw[1:]))
        elif raw.startswith("-") and old:
            removed.append((old, raw[1:]))
    return added, removed


def worktree_changes(base: str, cwd: Path):
    """Changes from base to the working tree, untracked files included (for the agent before a PR)."""
    changes = [(s, p) for s, p in ((l.split("\t")[0][0], l.split("\t")[-1]) for l in
               git("diff", "--name-status", "--no-renames", base, cwd=cwd).splitlines() if "\t" in l)]
    added, removed = diff_lines(base, None, cwd)
    counts = numstat(base, None, cwd)
    for path in git("ls-files", "--others", "--exclude-standard", cwd=cwd).splitlines():
        try:
            lines = (cwd / path).read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            lines = []
        changes.append(("A", path))
        added += [(path, l) for l in lines]
        counts[path] = (len(lines), 0)
    return changes, added, removed, counts


def size_findings(files_status: list[tuple[str, str]], counts: dict, cls: str, generated: list[str],
                  root: Path, risk_paths: dict) -> tuple[dict, list[dict], list[dict]]:
    """C9: (size summary, blocking findings, review findings)."""
    cfg = load_budget(root)
    if not cfg:
        return {"budget": "not configured"}, [], []
    budget = (cfg.get("budget") or {}).get(cls) or (cfg.get("budget") or {}).get("Routine", {})
    excluded = cfg.get("excluded", [])
    counted, gen, skipped = {}, [], []
    for _, path in files_status:
        if matches(path, generated):
            gen.append(path)
        elif matches(path, excluded):
            skipped.append(path)
        else:
            counted[path] = counts.get(path, (0, 0))
    lines = sum(a + d for a, d in counted.values())
    max_lines, max_files = budget.get("max_changed_lines"), budget.get("max_files")
    summary = {"risk_class_for_budget": cls, "changed_lines": lines, "files": len(counted),
               "max_changed_lines": max_lines, "max_files": max_files,
               "test_lines": sum(a + d for p, (a, d) in counted.items() if matches(p, TEST_PATHS)),
               "generated": gen, "excluded": skipped}
    blocking, review = [], []
    if (max_lines is not None and lines > max_lines) or (max_files is not None and len(counted) > max_files):
        blocking.append({"check": "review-budget",
                         "message": f"{lines} changed lines in {len(counted)} files. Budget for {cls}: "
                                    f"{max_lines} lines, {max_files} files. Split the change into increments "
                                    "(change-splitter skill), or record an exception.",
                         "files": [f"{p} (+{a} -{d})" for p, (a, d) in
                                   sorted(counted.items(), key=lambda kv: -sum(kv[1]))]})
    limit = cfg.get("max_new_file_lines")
    big = [f"{p} ({counts.get(p, (0, 0))[0]} lines)" for s, p in files_status
           if s == "A" and p in counted and limit is not None and counts.get(p, (0, 0))[0] > limit]
    if big:
        blocking.append({"check": "new-file-size",
                         "message": f"{len(big)} new file(s) above {limit} lines. Split the file, or list it "
                                    "under 'Generated files' in section 7 with its generator.",
                         "files": big})
    if gen:
        review.append({"check": "generated-files",
                       "message": f"{len(gen)} generated file(s) not counted. Check the generator command "
                                  "and its input, and spot-check the output.", "files": gen})
    # suggested review order: highest minimum risk class first, then governance files, then size
    def rank(path):
        _, why = minimum_class([path], risk_paths)
        cls_rank = class_rank(why[0][1]) if why else 0
        return (-cls_rank, not matches(path, GOVERNANCE_PATHS), matches(path, TEST_PATHS) is not None,
                -sum(counted.get(path, (0, 0))))
    order = sorted(counted, key=rank)
    summary["review_order"] = [f"{p} ({(minimum_class([p], risk_paths)[1] or [(p, 'Routine', '')])[0][1]}, "
                               f"+{counted[p][0]} -{counted[p][1]})" for p in order]
    return summary, blocking, review


def evaluate(values: dict, changes: list[tuple[str, str]], added: list, removed: list,
             root: Path, today: dt.date, counts: dict | None = None) -> dict:
    blocking, review, info = [], [], []
    problems: list[str] = []
    exception = cm.check_exception(values.get("Exception", "none") or "none", root, today, problems)
    spec_value = values.get("Specification", "")
    files = [p for _, p in changes]

    declared, permitted, spec_dir, ai_use = None, None, None, values.get("AI use", "").lower()
    generated, incs = [], {}
    increment = (values.get("Increment") or "").strip().upper()
    if spec_value and spec_value.lower() != "none" and (root / spec_value).is_file():
        meta, text = read_spec(root / spec_value)
        if meta and not meta.get("__invalid__"):
            declared = str(meta.get("risk_class", "")).strip()
            ai_use = str(meta.get("ai_use", "")).strip().lower()
            permitted = permitted_files(text)
            spec_dir = Path(spec_value).parent.name
            generated = generated_files(text)
            incs = increments(text)
            if increment and increment in incs and incs[increment]["files"]:
                permitted = incs[increment]["files"]          # narrow the scope to this increment
            elif increment and increment not in incs:
                info.append(f"Increment '{increment}' is not in section 8 of the specification.")
    elif spec_value.lower() == "none":
        declared = values.get("Risk class", "").strip()
    if declared is None:
        info.append("No readable specification or risk class. The metadata check reports this.")

    # scope (A1, C2): only for agent work that edits files
    if permitted is not None and ai_use in ("edit", "execute", "connected"):
        allowed = permitted + generated + [p.format(spec_dir=spec_dir) for p in ALWAYS_PERMITTED]
        outside = [f for f in files if not matches(f, allowed)]
        if outside:
            blocking.append({"check": "scope",
                             "message": f"{len(outside)} changed file(s) are not in "
                                        + (f"the files of {increment} (section 8)" if increment in incs
                                           else "section 7 of the specification"),
                             "files": outside})
        if not permitted:
            blocking.append({"check": "scope", "message": "Section 7 lists no permitted files", "files": []})

    # risk drift (C2)
    rated = [f for f in files if not matches(f, NOT_RISK_RATED)]
    risk_paths = load_risk_paths(root)
    minimum, reasons = minimum_class(rated, risk_paths)
    if declared in cm.RISK_CLASSES and class_rank(declared) < class_rank(minimum):
        drivers = [f"{f} ({cls}: {pat})" for f, cls, pat in reasons if cls == minimum]
        blocking.append({"check": "risk-drift",
                         "message": f"Declared risk class '{declared}' is lower than '{minimum}' for the changed paths",
                         "files": drivers})

    # tests removed (C4, principle 5)
    deleted_tests = [p for s, p in changes if s == "D" and matches(p, TEST_PATHS)]
    removed_defs = sum(1 for f, t in removed if TEST_DEF.search(t))
    added_defs = sum(1 for f, t in added if TEST_DEF.search(t))
    if deleted_tests or removed_defs > added_defs:
        review.append({"check": "tests-removed",
                       "message": f"{len(deleted_tests)} test file(s) deleted, "
                                  f"{removed_defs} test function(s) removed, {added_defs} added",
                       "files": deleted_tests})

    # suppressions added
    markers = [f"{f}: {SUPPRESSIONS.search(t).group(0)}" for f, t in added
               if SUPPRESSIONS.search(t) and not f.startswith(("tests/fixtures/", "evaluation/fixtures/"))
               and not f.endswith(".md") and f != "scripts/check_guardrails.py"]
    if markers:
        review.append({"check": "suppression-added", "message": f"{len(markers)} new suppression marker(s)",
                       "files": markers})

    # governance files changed (A7)
    gov = [f for f in files if matches(f, GOVERNANCE_PATHS)]
    if gov:
        review.append({"check": "governance-change",
                       "message": f"{len(gov)} governance or agent configuration file(s) changed. "
                                  "Code-owner review applies.", "files": gov})

    # reviewability gate (C9)
    size = {}
    if counts is not None:
        cls = declared if declared in RISK_CLASSES else "Routine"
        if class_rank(minimum) > class_rank(cls):
            cls = minimum
        size, size_block, size_review = size_findings(changes, counts, cls, generated, root, risk_paths)
        blocking += size_block
        review += size_review
    active = [i for i, v in incs.items() if v["status"] not in ("done", "merged")]
    if len(incs) > 1 and not increment:
        review.append({"check": "increment-missing",
                       "message": f"The specification has {len(incs)} increments ({len(active)} not done), "
                                  "but the pull request has no 'Increment:' line.", "files": []})

    accepted = bool(exception) and bool(blocking)
    if accepted:
        for b in blocking:
            b["accepted_by"] = values.get("Exception")
        review.extend(blocking)
        blocking = []
    return {"declared_class": declared, "minimum_class": minimum, "increment": increment or None,
            "size": size, "blocking": blocking, "review": review, "info": info + problems,
            "accepted_by_exception": accepted}


def report(result: dict) -> str:
    lines = ["### Change guardrails (C2, C4, C9, A1, A7)", "",
             f"Declared risk class: {result['declared_class'] or '(none)'} · "
             f"Minimum for changed paths: {result['minimum_class']}"
             + (f" · Increment: {result['increment']}" if result.get("increment") else ""), ""]
    s = result.get("size") or {}
    if "changed_lines" in s:
        lines += [f"Size (C9): {s['changed_lines']} of {s['max_changed_lines']} lines, {s['files']} of "
                  f"{s['max_files']} files for {s['risk_class_for_budget']}. Test lines: {s['test_lines']}. "
                  f"Not counted: {len(s['excluded'])} excluded, {len(s['generated'])} generated.", ""]
        if s.get("review_order"):
            lines += ["Suggested review order (highest risk first):"]
            lines += [f"{n}. {x}" for n, x in enumerate(s["review_order"][:15], 1)] + [""]
    for title, key in (("Blocking", "blocking"), ("Requires human review", "review")):
        lines.append(f"**{title}:** {len(result[key]) or 'none'}")
        for f in result[key]:
            note = f" (accepted by {f['accepted_by']})" if f.get("accepted_by") else ""
            lines.append(f"- `{f['check']}` {f['message']}{note}")
            lines += [f"  - {x}" for x in f["files"][:20]]
        lines.append("")
    lines += [f"Note: {i}" for i in result["info"]]
    lines.append("FAIL" if result["blocking"] else "PASS")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--event")
    ap.add_argument("--body-file")
    ap.add_argument("--spec", help="specification path, instead of a pull request body")
    ap.add_argument("--increment", help="increment ID with --spec, for example INC-2")
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--worktree", action="store_true", help="compare base with the working tree")
    ap.add_argument("--root", default=".")
    ap.add_argument("--today")
    ap.add_argument("--json-out")
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.root)
    if args.spec:
        values = {"Specification": args.spec, "Exception": "none", "Increment": args.increment or ""}
    else:
        values = cm.parse_body(cm.load_body(args))
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    try:
        if args.worktree:
            changes, added, removed, counts = worktree_changes(args.base, root)
        else:
            changes = changed_files(args.base, args.head, cwd=root)
            added, removed = diff_lines(args.base, args.head, root)
            counts = numstat(args.base, args.head, root)
    except subprocess.CalledProcessError as exc:
        print(f"git diff {args.base}...{args.head} failed: {exc.stderr.strip()}. "
              "Check the commit names. In CI, check out with fetch-depth: 0.", file=sys.stderr)
        return 2
    result = evaluate(values, changes, added, removed, root, today, counts)

    text = report(result)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2))
    return 0 if args.report_only or not result["blocking"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
