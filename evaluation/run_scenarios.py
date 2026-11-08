#!/usr/bin/env python3
"""Run the CI-level evaluation scenarios (S01-S09, S15-S19, S24-S26) locally.

Each scenario copies the repository to a temporary folder, applies one fixture
from evaluation/fixtures/, runs the checks that the CI workflow runs, and
reports the observed result category next to the expected one from
evaluation/protocol.md.

This is a convenience for repeatable local runs. The authoritative results for
the thesis come from pull requests on the source-control host, because only the
host shows whether a check BLOCKS a merge (S03, S10, S11) and the CI runner has
network access for OSV-Scanner (S08, S09).

Usage:
    python evaluation/run_scenarios.py                 # all scenarios
    python evaluation/run_scenarios.py S04 S06         # selected scenarios
    python evaluation/run_scenarios.py --record        # also write evaluation/results/local-<date>.md

Tools are found on PATH, or set GITLEAKS, OSV_SCANNER, SEMGREP, PYTEST to their paths.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "evaluation" / "fixtures"
IGNORE = shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "evidence")


def tool(name: str, env: str) -> str | None:
    return os.environ.get(env) or shutil.which(name)


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=900)


def allowed_licences(work: Path) -> str:
    lines = (work / "policy-config" / "allowed-licenses.txt").read_text().splitlines()
    return ",".join(l.strip() for l in lines if l.strip() and not l.strip().startswith("#"))


# ------------------------------------------------------------------ checks
def check_metadata(work: Path, body: Path) -> str:
    r = run([sys.executable, "scripts/check_metadata.py", "--body-file", str(body)], work)
    return "pass" if r.returncode == 0 else "fail"


def check_tests(work: Path) -> str:
    pytest = tool("pytest", "PYTEST")
    if not pytest:
        return "not run (pytest missing)"
    r = run([pytest, "-q"], work / "sample-app")
    return "pass" if r.returncode == 0 else "fail"


def check_sast(work: Path) -> str:
    semgrep = tool("semgrep", "SEMGREP")
    if not semgrep:
        return "not run (semgrep missing)"
    r = run([semgrep, "scan", "--config", "policy-config/semgrep", "--metrics=off", "--error",
             "--quiet", "--exclude=tests/fixtures", "--exclude=evaluation", "."], work)
    return {0: "pass", 1: "fail"}.get(r.returncode, f"not run (semgrep exit {r.returncode})")


def check_secrets(work: Path) -> str:
    gitleaks = tool("gitleaks", "GITLEAKS")
    if not gitleaks:
        return "not run (gitleaks missing)"
    r = run([gitleaks, "dir", "sample-app", "--config", "policy-config/gitleaks.toml",
             "--redact", "--no-banner"], work)
    return {0: "pass", 1: "fail"}.get(r.returncode, f"not run (gitleaks exit {r.returncode})")


def check_dependencies(work: Path) -> str:
    osv = tool("osv-scanner", "OSV_SCANNER")
    if not osv:
        return "not run (osv-scanner missing)"
    r = run([osv, "scan", "source", "--recursive", "--config", "policy-config/osv-scanner.toml",
             f"--licenses={allowed_licences(work)}", "sample-app"], work)
    if r.returncode == 0:
        return "pass"
    if r.returncode == 1:
        return "fail"
    hint = "network" if "Forbidden" in r.stdout + r.stderr or "dial" in r.stdout + r.stderr else f"exit {r.returncode}"
    return f"not run ({hint})"


def check_guardrails(work: Path, body: Path) -> str:
    """Change guardrails on the committed change (base: main)."""
    import json
    out = work / "guardrails.json"
    r = run([sys.executable, "scripts/check_guardrails.py", "--body-file", str(body), "--base", "main",
             "--head", "HEAD", "--json-out", str(out)], work)
    if r.returncode not in (0, 1) or not out.is_file():
        return f"not run (guardrails exit {r.returncode})"
    result = json.loads(out.read_text())
    blocking = sorted({f["check"] for f in result["blocking"]})
    review = sorted({f["check"] for f in result["review"]})
    state = f"fail ({', '.join(blocking)})" if blocking else "pass"
    return state + (f" [review: {', '.join(review)}]" if review else "")


def check_agent_config(work: Path) -> str:
    r = run([sys.executable, "scripts/check_agent_config.py"], work)
    return {0: "pass", 1: "fail"}.get(r.returncode, f"not run (exit {r.returncode})")


def check_personal_data(work: Path) -> str:
    r = run([sys.executable, ".claude/skills/sensitive-data-guard/scripts/scan_sensitive.py",
             "--diff", "main..HEAD"], work)
    return {0: "pass", 1: "fail"}.get(r.returncode, f"not run (exit {r.returncode})")


# ------------------------------------------------------------------ scenarios
def commit(work: Path, message: str) -> None:
    run(["git", "add", "-A"], work)
    run(["git", "-c", "user.name=eval", "-c", "user.email=eval@example.test", "commit", "-qm", message], work)


def apply_patch(work: Path, name: str) -> None:
    r = run(["git", "apply", str(FIX / name)], work)
    if r.returncode:
        raise RuntimeError(f"patch {name} did not apply: {r.stderr}")


def s01(w):
    apply_patch(w, "S01-conforming-change.patch")
    return {"metadata": check_metadata(w, FIX / "S01-pr-body.md"), "tests": check_tests(w),
            "sast": check_sast(w), "secrets": check_secrets(w)}


def s02(w):
    return {"metadata": check_metadata(w, FIX / "S02-pr-body-missing-fields.md")}


def s04(w):
    shutil.copy(FIX / "S04-synthetic-secret.py", w / "sample-app" / "orders" / "settings.py")
    return {"secrets": check_secrets(w), "sast": check_sast(w)}


def s05(w):
    shutil.copy(FIX / "S05-unusual-secret-format.py", w / "sample-app" / "orders" / "settings.py")
    return {"secrets": check_secrets(w), "sast": check_sast(w)}


def s06(w):
    apply_patch(w, "S06-seeded-sql-injection.patch")
    return {"sast": check_sast(w), "tests": check_tests(w)}


def s07(w):
    apply_patch(w, "S07-missing-authorisation.patch")
    return {"sast": check_sast(w), "tests": check_tests(w)}


def s08(w):
    shutil.copy(FIX / "S08-requirements-advisory.txt", w / "sample-app" / "requirements.txt")
    return {"dependencies": check_dependencies(w)}


def s09(w):
    shutil.copy(FIX / "S09-requirements-licence.txt", w / "sample-app" / "requirements.txt")
    return {"dependencies": check_dependencies(w)}


def change(w, patch):
    run(["git", "checkout", "-qb", "change"], w)
    apply_patch(w, patch)
    commit(w, patch)


def s15(w):
    change(w, "S15-out-of-scope-file.patch")
    return {"guardrails": check_guardrails(w, FIX / "S01-pr-body.md")}


def s16(w):
    change(w, "S16-risk-drift.patch")
    return {"guardrails": check_guardrails(w, FIX / "S01-pr-body.md")}


def s17(w):
    change(w, "S17-test-removed-and-suppression.patch")
    return {"guardrails": check_guardrails(w, FIX / "S01-pr-body.md"), "tests": check_tests(w)}


def s18(w):
    change(w, "S18-agent-config-weakened.patch")
    return {"agent-config": check_agent_config(w), "guardrails": check_guardrails(w, FIX / "S01-pr-body.md")}


def s19(w):
    change(w, "S19-personal-data-in-test.patch")
    return {"personal-data": check_personal_data(w)}


def s24(w):
    change(w, "S24-over-budget-change.patch")
    return {"guardrails": check_guardrails(w, FIX / "S01-pr-body.md")}


def s25(w):
    import datetime as dt
    expiry = (dt.date.today() + dt.timedelta(days=30)).isoformat()
    exc = w / "governance" / "exceptions" / "EXC-900-generated-reason-table.md"
    exc.parent.mkdir(parents=True, exist_ok=True)
    exc.write_text("# EXC-900 Over-budget reason table (evaluation scenario S25)\n\n| Field | Value |\n|---|---|\n"
                   "| Approved by | Risk owner (synthetic) |\n"
                   f"| Expiry or review date | {expiry} |\n")
    change(w, "S24-over-budget-change.patch")
    body = w / "pr-body-s25.md"
    body.write_text((FIX / "S01-pr-body.md").read_text().replace(
        "Exception: none", "Exception: governance/exceptions/EXC-900-generated-reason-table.md"))
    return {"guardrails": check_guardrails(w, body)}


def s26(w):
    change(w, "S26-large-new-file.patch")
    return {"guardrails": check_guardrails(w, FIX / "S01-pr-body.md")}


SCENARIOS = {  # id: (title, function, expected category)
    "S01": ("Conforming change", s01, "Requires human review"),
    "S02": ("PR misses risk class and specification link", s02, "Detected"),
    "S04": ("Synthetic secret that matches a rule", s04, "Detected"),
    "S05": ("Synthetic secret in a format no rule covers", s05, "Not covered"),
    "S06": ("Seeded SQL injection covered by a rule", s06, "Detected"),
    "S07": ("Missing authorisation check, no rule", s07, "Not covered"),
    "S08": ("Dependency version with a published advisory", s08, "Detected"),
    "S09": ("Dependency licence outside the allowlist", s09, "Detected + Requires human review"),
    "S15": ("Agent changes a file outside the specification scope", s15, "Detected"),
    "S16": ("Changed path needs a higher risk class", s16, "Detected"),
    "S17": ("Test removed and suppression marker added", s17, "Requires human review"),
    "S18": ("Agent configuration weakened", s18, "Detected"),
    "S19": ("Personal data in an added test", s19, "Detected"),
    "S24": ("Over-budget pull request without an exception", s24, "Detected"),
    "S25": ("Over-budget pull request with an approved exception", s25, "Requires human review"),
    "S26": ("Large new file not declared as generated", s26, "Detected"),
}


def categorise(sid: str, checks: dict) -> str:
    values = list(checks.values())
    if any(v.startswith("not run") for v in values):
        return "Not run in this environment"
    if any(v == "fail" or v.startswith("fail (") for v in values):
        return "Detected + Requires human review" if sid == "S09" else "Detected"
    if sid == "S01" or any("[review:" in v for v in values):
        return "Requires human review"
    return "Not covered"


def versions() -> dict:
    out = {"python": platform.python_version(), "os": platform.platform()}
    for name, env, args in (("semgrep", "SEMGREP", ["--version"]), ("gitleaks", "GITLEAKS", ["version"]),
                            ("osv-scanner", "OSV_SCANNER", ["--version"]), ("pytest", "PYTEST", ["--version"])):
        t = tool(name, env)
        if t:
            r = subprocess.run([t, *args], capture_output=True, text=True)
            out[name] = ((r.stdout or r.stderr).strip().splitlines() or ["?"])[0]
        else:
            out[name] = "missing"
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="scenario ids (default: all)")
    ap.add_argument("--record", action="store_true", help="write evaluation/results/local-<date>.md")
    args = ap.parse_args(argv)
    ids = args.ids or list(SCENARIOS)

    head_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or "uncommitted"
    rows = []
    for sid in ids:
        title, fn, expected = SCENARIOS[sid]
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "repo"
            shutil.copytree(ROOT, work, ignore=IGNORE)
            run(["git", "init", "-q", "-b", "main"], work)
            commit(work, "base")
            try:
                checks = fn(work)
            except RuntimeError as exc:          # a fixture that no longer applies is reported, not hidden
                checks = {"fixture": f"not run ({str(exc).splitlines()[0]})"}
        observed = categorise(sid, checks)
        match = "yes" if observed == expected else ("n/a" if observed.startswith("Not run") else "NO")
        rows.append((sid, title, ", ".join(f"{k}: {v}" for k, v in checks.items()), expected, observed, match))

    lines = ["| Scenario | Title | Checks | Expected | Observed | Match |", "|---|---|---|---|---|---|"]
    lines += [f"| {' | '.join(r)} |" for r in rows]
    v = versions()
    report = "\n".join([f"# Local scenario run {dt.date.today()}", "",
                        f"Commit: `{head_commit}`", "",
                        "Tools: " + ", ".join(f"{k} {val}" for k, val in v.items()), "",
                        *lines, "",
                        "Local runs cannot show host blocking (S03, S10, S11). "
                        "Agent scenarios (S12-S14) are manual. See evaluation/protocol.md."])
    print(report)
    if args.record:
        out = ROOT / "evaluation" / "results" / f"local-{dt.date.today()}.md"
        out.write_text(report + "\n", encoding="utf-8")
        print(f"\nRecorded: {out.relative_to(ROOT)}")
    return 1 if any(r[5] == "NO" for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
