"""Tests for scripts/check_guardrails.py with a temporary git repository."""
import datetime as dt
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_guardrails as cg  # noqa: E402
from spec_lib import changed_files, numstat  # noqa: E402

TODAY = dt.date(2026, 10, 26)
BODY = {"Specification": "specs/001-sample-change/spec.md", "Exception": "none"}


def sh(cwd, *args):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


class GuardrailTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for part in ("governance", "specs", "policy-config", "sample-app", "scripts"):
            shutil.copytree(ROOT / part, self.tmp / part,
                            ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
        sh(self.tmp, "git", "init", "-q", "-b", "main")
        sh(self.tmp, "git", "add", "-A")
        sh(self.tmp, "git", "-c", "user.name=t", "-c", "user.email=t@example.test", "commit", "-qm", "base")
        sh(self.tmp, "git", "checkout", "-qb", "change")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, rel, text, append=False):
        p = self.tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text((p.read_text() if append and p.exists() else "") + text)

    def evaluate(self, values=None):
        sh(self.tmp, "git", "add", "-A")
        sh(self.tmp, "git", "-c", "user.name=t", "-c", "user.email=t@example.test", "commit", "-q", "--allow-empty", "-m", "c")
        changes = changed_files("main", "HEAD", cwd=self.tmp)
        added, removed = cg.diff_lines("main", "HEAD", self.tmp)
        counts = numstat("main", "HEAD", self.tmp)
        return cg.evaluate(values or dict(BODY), changes, added, removed, self.tmp, TODAY, counts)

    def checks(self, result, key):
        return [f["check"] for f in result[key]]

    def test_in_scope_change_passes(self):
        self.write("sample-app/orders/store.py", "\n# refund total\n", append=True)
        r = self.evaluate()
        self.assertEqual(r["blocking"], [])
        self.assertEqual(r["minimum_class"], "Elevated")

    def test_spec_folder_is_always_in_scope(self):
        self.write("specs/001-sample-change/plan.md", "plan\n")
        self.assertEqual(self.evaluate()["blocking"], [])

    def test_out_of_scope_file_blocks(self):
        self.write("sample-app/orders/other.py", "x = 1\n")
        r = self.evaluate()
        self.assertIn("scope", self.checks(r, "blocking"))
        self.assertIn("sample-app/orders/other.py", r["blocking"][0]["files"])

    def test_risk_drift_blocks(self):
        spec = self.tmp / "specs/001-sample-change/spec.md"
        spec.write_text(spec.read_text().replace(
            "`sample-app/tests/test_store.py`", "`sample-app/tests/test_store.py`, `sample-app/auth/**`"))
        self.write("sample-app/auth/login.py", "x = 1\n")
        r = self.evaluate()
        self.assertEqual(self.checks(r, "blocking"), ["risk-drift"])
        self.assertEqual(r["minimum_class"], "High impact")

    def test_light_path_drift(self):
        values = {"Specification": "none", "Risk class": "Routine", "AI use": "suggest"}
        self.write("infra/main.tf", "x\n")
        self.assertIn("risk-drift", self.checks(self.evaluate(values), "blocking"))

    def test_light_path_routine_paths_pass(self):
        values = {"Specification": "none", "Risk class": "Routine", "AI use": "suggest"}
        self.write("docs/notes.md", "x\n")
        self.assertEqual(self.evaluate(values)["blocking"], [])

    def test_removed_test_is_review_not_blocking(self):
        (self.tmp / "sample-app/tests/test_store.py").unlink()
        r = self.evaluate()
        self.assertEqual(r["blocking"], [])
        self.assertIn("tests-removed", self.checks(r, "review"))

    def test_suppression_marker_is_review(self):
        self.write("sample-app/orders/store.py", "\nx = eval('1')  # nosemgrep\n", append=True)
        r = self.evaluate()
        self.assertIn("suppression-added", self.checks(r, "review"))

    def test_governance_change_is_review(self):
        spec = self.tmp / "specs/001-sample-change/spec.md"
        spec.write_text(spec.read_text().replace("`sample-app/tests/test_store.py`",
                                                 "`sample-app/tests/test_store.py`, `policy-config/**`"))
        self.write("policy-config/gitleaks.toml", "\n# change\n", append=True)
        r = self.evaluate()
        self.assertIn("governance-change", self.checks(r, "review"))

    def test_valid_exception_moves_blocking_to_review(self):
        self.write("governance/exceptions/EXC-001-test.md", "| Expiry or review date | 2026-12-31 |\n")
        self.write("sample-app/orders/other.py", "x = 1\n")
        values = dict(BODY, Exception="governance/exceptions/EXC-001-test.md")
        r = self.evaluate(values)
        self.assertEqual(r["blocking"], [])
        self.assertTrue(r["accepted_by_exception"])
        self.assertIn("scope", self.checks(r, "review"))

    def test_expired_exception_does_not_accept(self):
        self.write("governance/exceptions/EXC-001-test.md", "| Expiry or review date | 2026-01-31 |\n")
        self.write("sample-app/orders/other.py", "x = 1\n")
        r = self.evaluate(dict(BODY, Exception="governance/exceptions/EXC-001-test.md"))
        self.assertIn("scope", self.checks(r, "blocking"))

    # ------------------------------------------------------------ C9 reviewability gate
    def spec_edit(self, old, new):
        spec = self.tmp / "specs/001-sample-change/spec.md"
        text = spec.read_text()
        self.assertIn(old, text)
        spec.write_text(text.replace(old, new, 1))

    def lines(self, n, prefix="x"):
        return "".join(f"{prefix}_{i} = {i}\n" for i in range(n))

    def test_size_summary_and_review_order(self):
        self.write("sample-app/orders/store.py", "\n# refund\n", append=True)
        self.write("sample-app/tests/test_store.py", "\n# more\n", append=True)
        r = self.evaluate()
        s = r["size"]
        self.assertEqual((s["changed_lines"], s["files"], s["max_changed_lines"]), (4, 2, 400))
        self.assertTrue(s["review_order"][0].startswith("sample-app/orders/store.py (Elevated"))

    def test_over_line_budget_blocks(self):
        self.write("sample-app/orders/store.py", self.lines(450), append=True)
        r = self.evaluate()
        self.assertEqual(self.checks(r, "blocking"), ["review-budget"])
        self.assertIn("change-splitter", r["blocking"][0]["message"])

    def test_over_file_budget_blocks(self):
        self.spec_edit("`sample-app/tests/test_store.py` |", "`sample-app/tests/test_store.py`, `sample-app/orders/m*.py` |")
        for i in range(16):
            self.write(f"sample-app/orders/m{i}.py", "x = 1\n")
        self.assertIn("review-budget", self.checks(self.evaluate(), "blocking"))

    def test_high_impact_has_smaller_budget(self):
        self.spec_edit("risk_class: Elevated", "risk_class: High impact")
        self.write("sample-app/orders/store.py", self.lines(250), append=True)
        r = self.evaluate()
        self.assertIn("review-budget", self.checks(r, "blocking"))
        self.assertEqual(r["size"]["max_changed_lines"], 200)

    def test_large_new_file_blocks(self):
        self.spec_edit("`sample-app/tests/test_store.py` |", "`sample-app/tests/test_store.py`, `sample-app/orders/rates.py` |")
        self.write("sample-app/orders/rates.py", self.lines(320))
        self.assertEqual(self.checks(self.evaluate(), "blocking"), ["new-file-size"])

    def test_declared_generated_file_is_not_counted(self):
        self.spec_edit("| Generated files | none |",
                       "| Generated files | `sample-app/orders/rates_gen.py` — produced by `python tools/gen.py` |")
        self.write("sample-app/orders/rates_gen.py", self.lines(1000))
        r = self.evaluate()
        self.assertEqual(r["blocking"], [])
        self.assertIn("generated-files", self.checks(r, "review"))
        self.assertEqual(r["size"]["changed_lines"], 0)

    def test_lockfile_is_excluded(self):
        self.spec_edit("`sample-app/tests/test_store.py` |", "`sample-app/tests/test_store.py`, `sample-app/package-lock.json` |")
        self.write("sample-app/package-lock.json", self.lines(900))
        r = self.evaluate()
        self.assertEqual(r["blocking"], [])
        self.assertIn("sample-app/package-lock.json", r["size"]["excluded"])

    def test_exception_accepts_over_budget(self):
        self.write("governance/exceptions/EXC-001-test.md", "| Expiry or review date | 2026-12-31 |\n")
        self.write("sample-app/orders/store.py", self.lines(450), append=True)
        r = self.evaluate(dict(BODY, Exception="governance/exceptions/EXC-001-test.md"))
        self.assertEqual(r["blocking"], [])
        self.assertIn("review-budget", self.checks(r, "review"))

    def add_two_increments(self):
        self.spec_edit("## 9. Open questions", """## 8. Increments (C9)

| ID | Reviewable result | Files | Estimated changed lines | Depends on | Status |
|---|---|---|---|---|---|
| INC-1 | Store logic | `sample-app/orders/store.py` | ~150 | — | done |
| INC-2 | Tests | `sample-app/tests/test_store.py` | ~100 | INC-1 | planned |

## 9. Open questions""")

    def test_increment_narrows_scope(self):
        # replace the existing single-increment section of the sample spec
        spec = self.tmp / "specs/001-sample-change/spec.md"
        text = spec.read_text()
        start, end = text.index("## 8. Increments"), text.index("## 9. Open questions")
        spec.write_text(text[:start] + text[end:])
        self.add_two_increments()
        self.write("sample-app/tests/test_store.py", "\n# more\n", append=True)
        r = self.evaluate(dict(BODY, Increment="INC-1"))
        self.assertIn("scope", self.checks(r, "blocking"))
        self.assertIn("INC-1", r["blocking"][0]["message"])
        self.assertEqual(self.evaluate(dict(BODY, Increment="INC-2"))["blocking"], [])

    def test_missing_increment_line_is_review(self):
        spec = self.tmp / "specs/001-sample-change/spec.md"
        text = spec.read_text()
        start, end = text.index("## 8. Increments"), text.index("## 9. Open questions")
        spec.write_text(text[:start] + text[end:])
        self.add_two_increments()
        self.write("sample-app/orders/store.py", "\n# x\n", append=True)
        self.assertIn("increment-missing", self.checks(self.evaluate(), "review"))

    def test_worktree_mode_counts_uncommitted_and_untracked(self):
        self.write("sample-app/orders/store.py", self.lines(5), append=True)
        self.write("sample-app/orders/new_mod.py", self.lines(7))
        changes, added, removed, counts = cg.worktree_changes("main", self.tmp)
        self.assertIn(("A", "sample-app/orders/new_mod.py"), changes)
        self.assertEqual(counts["sample-app/orders/new_mod.py"], (7, 0))
        self.assertEqual(counts["sample-app/orders/store.py"][0], 5)

    def test_cli_spec_mode_worktree(self):
        self.write("sample-app/orders/store.py", self.lines(450), append=True)
        rc = cg.main(["--spec", "specs/001-sample-change/spec.md", "--base", "main", "--worktree",
                      "--root", str(self.tmp)])
        self.assertEqual(rc, 1)

    def test_removed_lines_of_deleted_file_are_attributed(self):
        (self.tmp / "sample-app/tests/test_store.py").unlink()
        sh(self.tmp, "git", "add", "-A")
        sh(self.tmp, "git", "-c", "user.name=t", "-c", "user.email=t@example.test", "commit", "-qm", "d")
        _, removed = cg.diff_lines("main", "HEAD", self.tmp)
        self.assertTrue(any(f == "sample-app/tests/test_store.py" for f, _ in removed))

    def test_report_text(self):
        self.write("sample-app/orders/other.py", "x = 1\n")
        text = cg.report(self.evaluate())
        self.assertIn("FAIL", text)
        self.assertIn("`scope`", text)


if __name__ == "__main__":
    unittest.main()
