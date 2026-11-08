#!/usr/bin/env python3
"""C7 — Write the per-change evidence summary.

Collects the pull request metadata (read from the specification), the guardrail
findings that need human review, and the result of each CI job into
evidence-summary.md and evidence-summary.json. The summary links results to one
commit. It is not an audit trail and it does not contain prompts, code or
personal data (see docs/evidence-format.md).

Usage (GitHub Actions):
    NEEDS_JSON='${{ toJSON(needs) }}' python scripts/evidence_summary.py \
        --metadata metadata.json --guardrails guardrails.json --out-dir evidence

Environment read: NEEDS_JSON, GITHUB_REPOSITORY, GITHUB_SHA, PR_NUMBER, PR_HEAD_SHA,
GITHUB_RUN_ID, GITHUB_SERVER_URL, and tool versions *_VERSION.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path

CHECKS = [  # job id -> (label, control)
    ("metadata", "Governance metadata", "C2, C7"),
    ("guardrails", "Change guardrails (scope, risk drift, change size, agent configuration)", "C2, C4, C9, A1, A7"),
    ("secrets", "Secrets and personal data (gitleaks, sensitive-data patterns)", "C3, C4"),
    ("dependencies", "Dependencies and licences (OSV-Scanner)", "C5"),
    ("tests-sast", "Tests and SAST (pytest, Semgrep)", "C4"),
]
TOOLS = ["PYTHON_VERSION", "SEMGREP_VERSION", "GITLEAKS_VERSION", "OSV_SCANNER_VERSION"]


def build(metadata: dict, needs: dict, env: dict, guardrails: dict | None = None) -> dict:
    values = metadata.get("values", {})
    head = env.get("PR_HEAD_SHA") or env.get("GITHUB_SHA", "unknown")
    run_url = ""
    if env.get("GITHUB_SERVER_URL") and env.get("GITHUB_REPOSITORY") and env.get("GITHUB_RUN_ID"):
        run_url = f"{env['GITHUB_SERVER_URL']}/{env['GITHUB_REPOSITORY']}/actions/runs/{env['GITHUB_RUN_ID']}"
    checks = []
    for job, label, control in CHECKS:
        result = (needs.get(job) or {}).get("result", "not run")
        checks.append({"job": job, "check": label, "control": control, "result": result})
    return {
        "repository": env.get("GITHUB_REPOSITORY", "unknown"),
        "pull_request": env.get("PR_NUMBER", "unknown"),
        "commit": head,
        "run": run_url,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "metadata_source": values.get("Source", "pull request"),
        "metadata": {f: values.get(f) or "(missing)" for f in
                     ["Specification", "Risk class", "Data class", "AI use", "AI tool", "Capability profile",
                      "Exception"]},
        "metadata_problems": metadata.get("problems", []),
        "checks": checks,
        "review_items": [{"check": r["check"], "message": r["message"], "accepted_by": r.get("accepted_by")}
                         for r in (guardrails or {}).get("review", [])],
        "minimum_risk_class": (guardrails or {}).get("minimum_class", "not computed"),
        "increment": (guardrails or {}).get("increment"),
        "size": (guardrails or {}).get("size") or {},
        "tools": {t.replace("_VERSION", "").lower(): env.get(t, "unknown") for t in TOOLS},
        "human_approval": "Recorded by the source-control host in the pull request; not part of this summary.",
    }


def to_markdown(e: dict) -> str:
    out = ["# Evidence summary", "",
           f"Repository: `{e['repository']}` · Pull request: #{e['pull_request']} · Commit: `{e['commit']}`", ""]
    if e["run"]:
        out += [f"CI run: {e['run']}", ""]
    out += [f"## Declared metadata (from the {e.get('metadata_source', 'pull request')})", "",
            "| Field | Value |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in e["metadata"].items()]
    if e["metadata_problems"]:
        out += ["", "Metadata problems:"] + [f"- {p}" for p in e["metadata_problems"]]
    out += ["", f"Minimum risk class for the changed paths: {e.get('minimum_risk_class', 'not computed')}"]
    out += ["", "## Check results", "", "| Check | Control | Result |", "|---|---|---|"]
    out += [f"| {c['check']} | {c['control']} | {c['result']} |" for c in e["checks"]]
    s = e.get("size") or {}
    if "changed_lines" in s:
        out += ["", "## Size and review order (C9)", "",
                f"{s['changed_lines']} of {s['max_changed_lines']} changed lines, {s['files']} of {s['max_files']} "
                f"files (budget for {s['risk_class_for_budget']})"
                + (f", increment {e['increment']}" if e.get("increment") else "") + ". "
                f"Test lines: {s['test_lines']}. Line counts only approximate the review effort.", ""]
        if s.get("review_order"):
            out += ["Suggested review order (highest risk first):", ""]
            out += [f"{n}. `{x}`" for n, x in enumerate(s["review_order"][:20], 1)]
        if s.get("generated"):
            out += ["", "Generated, not counted: " + ", ".join(f"`{g}`" for g in s["generated"])]
    out += ["", "## Requires human review", ""]
    if e.get("review_items"):
        out += [f"- `{r['check']}` {r['message']}" + (f" (accepted by {r['accepted_by']})" if r.get("accepted_by") else "")
                for r in e["review_items"]]
    else:
        out += ["- No guardrail findings. The reviewer still reads every changed line."]
    out += ["", "## Tool versions", "", "| Tool | Version |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in e["tools"].items()]
    out += ["", "## Not in this summary", "",
            f"- Human approval: {e['human_approval']}",
            "- Raw prompts, model output, source code and personal data.",
            "- Any claim about which lines a model wrote.", "",
            f"Generated at {e['generated_at']}. A passed check does not prove that the change is correct or secure."]
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--metadata", required=True, help="JSON written by check_metadata.py --json-out")
    ap.add_argument("--guardrails", help="JSON written by check_guardrails.py --json-out (optional)")
    ap.add_argument("--out-dir", default="evidence")
    args = ap.parse_args(argv)

    meta_path = Path(args.metadata)
    metadata = json.loads(meta_path.read_text()) if meta_path.is_file() else {"values": {}, "problems": ["metadata.json missing"]}
    needs = json.loads(os.environ.get("NEEDS_JSON") or "{}")
    guard_path = Path(args.guardrails) if args.guardrails else None
    guardrails = json.loads(guard_path.read_text()) if guard_path and guard_path.is_file() else None
    evidence = build(metadata, needs, dict(os.environ), guardrails)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    md = to_markdown(evidence)
    (out / "evidence-summary.md").write_text(md, encoding="utf-8")
    (out / "evidence-summary.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
