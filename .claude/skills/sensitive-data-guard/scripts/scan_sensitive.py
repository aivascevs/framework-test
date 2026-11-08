#!/usr/bin/env python3
"""Scan text for secrets and personal data (C3, A4). Standard library only.

Used by the sensitive-data-guard skill (the agent runs it on its own changes)
and by CI (the "Secrets and personal data" job). The output names the KIND and
the LOCATION of each finding. It never prints the value.

Usage:
    scan_sensitive.py FILE [FILE ...]          scan whole files
    scan_sensitive.py --diff BASE..HEAD        scan only lines added between two commits
    scan_sensitive.py --staged                 scan lines added in the git index
    scan_sensitive.py --worktree               scan lines added since HEAD (staged and unstaged)
    scan_sensitive.py --stdin                  scan text from standard input
Options:
    --json            machine-readable output
    --exclude GLOB    skip paths (repeatable). Defaults skip synthetic test fixtures.

Exit codes: 0 no findings, 1 findings, 2 usage error.

A line that contains the marker "sensitive-data: synthetic" is skipped. CI reports
every new marker to the reviewer (scripts/check_guardrails.py), so the marker
cannot hide data silently.

Limits: patterns find only the formats they describe. A clean result does not
prove that no sensitive data is present. Real names, addresses and free-text
personal data need human judgement.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SYNTHETIC_MARKER = "sensitive-data: synthetic"
DEFAULT_EXCLUDES = ["evaluation/fixtures/*", "tests/fixtures/*", "*.png", "*.svg", "*.lock",
                    "*/.pytest_cache/*", "*/__pycache__/*", "*/node_modules/*", ".git/*"]
RESERVED_EMAIL_DOMAINS = re.compile(
    r"@(?:[\w-]+\.)*(?:example\.(?:com|org|net)|example|test|invalid|localhost|"
    r"users\.noreply\.github\.com|anthropic\.com)$", re.I)


# ----------------------------------------------------------------- validators
def luhn_ok(digits: str) -> bool:
    nums = [int(d) for d in digits if d.isdigit()]
    if not 13 <= len(nums) <= 19:
        return False
    total = 0
    for i, n in enumerate(reversed(nums)):
        if i % 2:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0 and len(set(nums)) > 1


def iban_ok(value: str) -> bool:
    s = re.sub(r"\s", "", value).upper()
    if not 15 <= len(s) <= 34:
        return False
    moved = s[4:] + s[:4]
    try:
        number = int("".join(str(int(c, 36)) for c in moved))
    except ValueError:
        return False
    return number % 97 == 1


def lv_personal_code_ok(value: str) -> bool:
    """Latvian personal code. New-format codes (32xxxx-xxxxx) have no date and no check digit."""
    digits = value.replace("-", "")
    if digits.startswith("32"):
        return True
    day, month = int(digits[0:2]), int(digits[2:4])
    if not (1 <= day <= 31 and 1 <= month <= 12):
        return False
    weights = [1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check = (1101 - sum(int(d) * w for d, w in zip(digits[:10], weights))) % 11
    return check == int(digits[10])


def email_ok(value: str) -> bool:
    return not RESERVED_EMAIL_DOMAINS.search(value)


@dataclass(frozen=True)
class Rule:
    id: str
    kind: str          # secret | personal
    pattern: re.Pattern
    validator: object = None
    group: int = 0


RULES = [
    Rule("private-key", "secret", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY")),
    Rule("aws-access-key-id", "secret", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    Rule("github-token", "secret", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})\b")),
    Rule("jwt", "secret", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    Rule("connection-string-password", "secret",
         re.compile(r"(?i)\b(?:password|pwd)\s*=\s*([^;'\"\s]{6,})")),
    Rule("credential-assignment", "secret",
         re.compile(r"(?i)\b[\w.]*(?:password|passwd|secret|api_?key|access_?token|private_?key)[\w.]*\s*[:=]\s*[\"']([^\"'\s]{8,})[\"']"),
         group=1),
    Rule("email-address", "personal", re.compile(r"\b[\w.+-]+@(?:[\w-]+\.)+[A-Za-z]{2,24}\b"), email_ok),
    Rule("iban", "personal", re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}(?:[ ]?[A-Z0-9]{1,4})?\b"), iban_ok),
    Rule("payment-card", "personal", re.compile(r"\b(?:\d[ -]?){12,18}\d\b"), luhn_ok),
    Rule("lv-personal-code", "personal", re.compile(r"\b\d{6}-\d{5}\b"), lv_personal_code_ok),
    Rule("phone-number", "personal", re.compile(r"(?<![\w+])\+(?:371[ ]?\d{8}|[1-9]\d{1,2}[ ]?\d{3}[ ]?\d{3,4}[ ]?\d{2,4})\b")),
]


@dataclass
class Finding:
    rule: str
    kind: str
    file: str
    line: int
    column: int
    hint: str          # redacted: first two characters and length only


def redact(value: str) -> str:
    v = value.strip()
    return f"{v[:2]}… ({len(v)} chars)"


def scan_text(text: str, filename: str, line_offsets: dict[int, int] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    for idx, line in enumerate(text.splitlines(), 1):
        if SYNTHETIC_MARKER in line:
            continue
        lineno = line_offsets.get(idx, idx) if line_offsets else idx
        for rule in RULES:
            for m in rule.pattern.finditer(line):
                value = m.group(rule.group) if rule.group else m.group(0)
                if rule.validator and not rule.validator(value):
                    continue
                findings.append(Finding(rule.id, rule.kind, filename, lineno, m.start() + 1, redact(value)))
    return findings


def excluded(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def added_lines(diff_args: list[str]) -> dict[str, list[tuple[int, str]]]:
    """Return {file: [(line_number, text), ...]} for lines added in a git diff."""
    out = subprocess.run(["git", "diff", "--unified=0", "--no-color", *diff_args],
                         capture_output=True, text=True, check=True).stdout
    result: dict[str, list[tuple[int, str]]] = {}
    current, lineno = None, 0
    for raw in out.splitlines():
        if raw.startswith("+++ "):
            current = raw[6:] if raw.startswith("+++ b/") else None
            continue
        if raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            lineno = int(m.group(1)) if m else 0
            continue
        if current and raw.startswith("+") and not raw.startswith("+++"):
            result.setdefault(current, []).append((lineno, raw[1:]))
            lineno += 1
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--diff", metavar="BASE..HEAD")
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--worktree", action="store_true")
    mode.add_argument("--stdin", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--exclude", action="append", default=None)
    args = ap.parse_args(argv)
    excludes = DEFAULT_EXCLUDES if args.exclude is None else args.exclude

    findings: list[Finding] = []
    if args.stdin:
        findings = scan_text(sys.stdin.read(), "<stdin>")
    elif args.diff or args.staged or args.worktree:
        diff_args = ([args.diff.replace("..", "...", 1)] if args.diff and "..." not in args.diff
                     else [args.diff] if args.diff else ["--cached"] if args.staged else ["HEAD"])
        try:
            changed = added_lines(diff_args)
        except subprocess.CalledProcessError as exc:
            print(f"git diff {' '.join(diff_args)} failed: {exc.stderr.strip()}", file=sys.stderr)
            return 2
        for path, lines in changed.items():
            if excluded(path, excludes):
                continue
            text = "\n".join(t for _, t in lines)
            offsets = {i: n for i, (n, _) in enumerate(lines, 1)}
            findings += scan_text(text, path, offsets)
    elif args.paths:
        for p in args.paths:
            path = Path(p)
            files = [f for f in path.rglob("*") if f.is_file()] if path.is_dir() else [path]
            for f in files:
                rel = f.as_posix().removeprefix("./")
                if excluded(rel, excludes) or excluded("./" + rel, excludes):
                    continue
                try:
                    findings += scan_text(f.read_text(encoding="utf-8"), rel)
                except (UnicodeDecodeError, OSError):
                    continue
    else:
        ap.print_usage(sys.stderr)
        return 2

    if args.json:
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        for f in findings:
            print(f"{f.file}:{f.line}:{f.column} {f.kind} {f.rule} [{f.hint}]")
        print(f"\n{len(findings)} finding(s). Values are not shown. "
              "A clean result does not prove that no sensitive data is present.")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
