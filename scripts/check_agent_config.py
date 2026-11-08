#!/usr/bin/env python3
"""A7 — Check that the agent configuration in the repository is not weaker than the baseline.

Compares .claude/settings.json, .vscode/settings.json and the read-only subagents
in .claude/agents with policy-config/agent-baseline.yaml. Fails when a setting is
missing or weaker. Assurance mode: Detected. The check sees only the repository
files. User, local and managed settings on a developer machine can differ.

Usage:
    check_agent_config.py [--root .] [--json-out agent-config.json] [--report-only]
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

import yaml


def strip_jsonc(text: str) -> str:
    """Remove // and /* */ comments and trailing commas outside strings."""
    out, i, in_str = [], 0, False
    while i < len(text):
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\":
                out.append(text[i + 1])
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            out.append(c)
        elif text.startswith("//", i):
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        elif text.startswith("/*", i):
            i = text.find("*/", i) + 2
            continue
        else:
            out.append(c)
        i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(strip_jsonc(path.read_text(encoding="utf-8")))


def get(data: dict, dotted: str, flat: bool = False):
    if flat:
        return data.get(dotted, "<missing>")
    cur = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return "<missing>"
        cur = cur[part]
    return cur


def check_claude(cfg: dict, data: dict | None, problems: list[str]) -> None:
    f = cfg["file"]
    if data is None:
        problems.append(f"{f} is missing.")
        return
    for key, want in cfg.get("required", {}).items():
        have = get(data, key)
        if have != want:
            problems.append(f"{f}: '{key}' is {json.dumps(have)}, the baseline needs {json.dumps(want)}.")
    perms = data.get("permissions", {})
    deny, ask, allow = perms.get("deny", []), perms.get("ask", []), perms.get("allow", [])
    for rule in cfg.get("deny_must_include", []):
        if rule not in deny:
            problems.append(f"{f}: deny rule '{rule}' is missing.")
    for rule in cfg.get("ask_or_deny_must_include", []):
        if rule not in ask and rule not in deny:
            problems.append(f"{f}: '{rule}' must be in 'ask' or 'deny'.")
    for rule in allow:
        for pat in cfg.get("allow_must_not_match", []):
            if re.search(pat, rule):
                problems.append(f"{f}: allow rule '{rule}' is too broad (baseline pattern {pat}).")
    domains = get(data, "sandbox.network.allowedDomains")
    extra = sorted(set(domains if isinstance(domains, list) else []) - set(cfg.get("allowed_domains_max", [])))
    if extra:
        problems.append(f"{f}: sandbox domains not in the baseline: {', '.join(extra)}.")
    hooks = data.get("hooks", {})
    for event, script in cfg.get("hooks_must_include", {}).items():
        commands = [h.get("command", "") for m in hooks.get(event, []) for h in m.get("hooks", [])]
        if not any(script in c for c in commands):
            problems.append(f"{f}: hook {event} must run {script}.")


def check_vscode(cfg: dict, data: dict | None, problems: list[str]) -> None:
    f = cfg["file"]
    if data is None:
        problems.append(f"{f} is missing.")
        return
    for key, want in cfg.get("required", {}).items():
        have = get(data, key, flat=True)
        if have != want:
            problems.append(f"{f}: '{key}' is {json.dumps(have)}, the baseline needs {json.dumps(want)}.")
    rules = data.get("chat.tools.terminal.autoApprove", {}) or {}
    for key in cfg.get("auto_approve_must_be_false", []):
        if rules.get(key) is not False:
            problems.append(f"{f}: terminal rule {key} must be false (ask for approval).")
    for key, value in rules.items():
        if value is True:
            for pat in cfg.get("auto_approve_true_must_not_match", []):
                if re.search(pat, key):
                    problems.append(f"{f}: terminal rule {key} auto-approves too much (baseline pattern {pat}).")
    domains = data.get("chat.agent.sandbox.network.allowedDomains", []) or []
    extra = sorted(set(domains) - set(cfg.get("allowed_domains_max", [])))
    if extra:
        problems.append(f"{f}: sandbox domains not in the baseline: {', '.join(extra)}.")


def agent_tools(path: Path) -> list[str] | None:
    m = re.match(r"\A---\s*\n(.*?)\n---", path.read_text(encoding="utf-8"), re.S)
    if not m:
        return None
    tools = (yaml.safe_load(m.group(1)) or {}).get("tools")
    if tools is None:
        return None                       # no tools line: the agent inherits every tool
    return [t.strip() for t in (tools.split(",") if isinstance(tools, str) else tools)]


def check_agents(cfg: dict, root: Path, problems: list[str]) -> None:
    folder = root / cfg["folder"]
    for name in cfg.get("read_only", []):
        path = folder / f"{name}.md"
        if not path.is_file():
            problems.append(f"{cfg['folder']}/{name}.md is missing.")
            continue
        tools = agent_tools(path)
        if tools is None:
            problems.append(f"{cfg['folder']}/{name}.md has no 'tools:' list, so it gets every tool.")
            continue
        extra = sorted(set(tools) - set(cfg.get("read_only_tools", [])))
        if extra:
            problems.append(f"{cfg['folder']}/{name}.md must stay read-only. Extra tools: {', '.join(extra)}.")


def check(root: Path) -> list[str]:
    base = yaml.safe_load((root / "policy-config" / "agent-baseline.yaml").read_text()) or {}
    problems: list[str] = []
    for key, fn in (("claude_code", check_claude), ("vscode", check_vscode)):
        if key in base:
            cfg = base[key]
            try:
                data = load_json(root / cfg["file"])
            except json.JSONDecodeError as exc:
                problems.append(f"{cfg['file']} is not valid JSON: {exc}.")
                continue
            fn(cfg, data, problems)
    if "agents" in base:
        check_agents(base["agents"], root, problems)
    for f in base.get("forbidden_files", []):
        if (root / f).exists():
            problems.append(f"{f} exists. MCP configuration needs an approved specification and an exception (A5).")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--json-out")
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args(argv)
    problems = check(Path(args.root))
    lines = ["### Agent configuration (A7)", ""]
    lines += ([f"FAIL — {len(problems)} setting(s) weaker than policy-config/agent-baseline.yaml:"]
              + [f"- {p}" for p in problems]) if problems else ["PASS — agent settings meet the baseline."]
    text = "\n".join(lines)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps({"problems": problems}, indent=2))
    return 0 if args.report_only or not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
