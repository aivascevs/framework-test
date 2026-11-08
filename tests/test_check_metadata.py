"""Tests for scripts/check_metadata.py. Run from the repository root:

    python -m unittest discover -s tests -v
"""
import datetime as dt
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_metadata as cm  # noqa: E402

TODAY = dt.date(2026, 10, 26)

GOOD_BODY = """## Summary
Adds refund total.

## Change metadata
<!-- comment with Specification: none must be ignored -->
Specification: specs/001-sample-change/spec.md
Exception: none
"""

LIGHT_BODY = ("Specification: none\nRisk class: Routine\nAI use: suggest\nAI tool: github-copilot\n"
              "Capability profile: P0\nException: none\n")


def run(body, root=ROOT, today=TODAY):
    return cm.check(cm.parse_body(body), root, today)


def problems(body, root=ROOT, today=TODAY):
    return run(body, root, today)[0]


class ParseTests(unittest.TestCase):
    def test_reads_fields_and_ignores_comments(self):
        v = cm.parse_body(GOOD_BODY)
        self.assertEqual(v["Specification"], "specs/001-sample-change/spec.md")
        self.assertNotIn("Risk class", v)

    def test_accepts_bold_bullet_form(self):
        self.assertEqual(cm.parse_body("- **Risk class:** Routine")["Risk class"], "Routine")


class SpecPathTests(unittest.TestCase):
    def test_spec_link_alone_passes_and_resolves_values(self):
        p, resolved = run(GOOD_BODY)
        self.assertEqual(p, [])
        self.assertEqual(resolved["Source"], "specification")
        self.assertEqual(resolved["Risk class"], "Elevated")
        self.assertEqual(resolved["AI tool"], "claude-code")
        self.assertEqual(resolved["Capability profile"], "P1")
        self.assertEqual(resolved["Data class"], "internal")

    def test_template_body_fails(self):
        body = (ROOT / ".github" / "pull_request_template.md").read_text()
        self.assertTrue(any("does not exist" in x for x in problems(body)))

    def test_missing_specification_line(self):
        p = problems("Exception: none\n")
        self.assertTrue(any("'Specification: <path>' is missing" in x for x in p), p)

    def test_repeated_value_that_matches_passes(self):
        self.assertEqual(problems(GOOD_BODY + "Risk class: Elevated\nAI use: edit\n"), [])

    def test_repeated_value_that_differs_fails(self):
        p = problems(GOOD_BODY + "Risk class: Routine\n")
        self.assertTrue(any("differs from the specification" in x for x in p), p)


class LightPathTests(unittest.TestCase):
    def test_routine_suggest_passes(self):
        p, resolved = run(LIGHT_BODY)
        self.assertEqual(p, [])
        self.assertEqual(resolved["AI use"], "suggest")

    def test_no_ai_passes(self):
        body = ("Specification: none\nRisk class: Routine\nAI use: none\nAI tool: none\n"
                "Capability profile: n/a\n")
        self.assertEqual(problems(body), [])

    def test_light_path_needs_routine(self):
        p = problems(LIGHT_BODY.replace("Routine", "Elevated"))
        self.assertTrue(any("only with 'Risk class: Routine'" in x for x in p), p)

    def test_light_path_refuses_agent_edits(self):
        p = problems(LIGHT_BODY.replace("AI use: suggest", "AI use: edit").replace("P0", "P1"))
        self.assertTrue(any("/new-change" in x for x in p), p)

    def test_unapproved_tool(self):
        p = problems(LIGHT_BODY.replace("github-copilot", "some-chatbot"))
        self.assertTrue(any("not in governance/approved-tools.yaml" in x for x in p), p)

    def test_profile_must_match_use(self):
        self.assertTrue(any("does not match AI use" in x for x in problems(LIGHT_BODY.replace("P0", "P2"))))


class SpecContentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for part in ("governance", "specs"):
            shutil.copytree(ROOT / part, self.tmp / part)
        self.spec = self.tmp / "specs" / "001-sample-change" / "spec.md"

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def edit_spec(self, old, new):
        self.spec.write_text(self.spec.read_text().replace(old, new))

    def p(self, body=GOOD_BODY):
        return problems(body, self.tmp)

    def test_draft_spec_fails(self):
        self.edit_spec("status: approved", "status: draft")
        self.assertTrue(any("not 'approved'" in x for x in self.p()))

    def test_unknown_risk_class(self):
        self.edit_spec("risk_class: Elevated", "risk_class: Medium")
        self.assertTrue(any("not one of" in x for x in self.p()))

    def test_mode_not_permitted(self):
        self.edit_spec("ai_use: edit", "ai_use: connected")
        self.edit_spec("capability_profile: P1", "capability_profile: P3")
        self.assertTrue(any("not a permitted mode" in x for x in self.p()))

    def test_elevated_needs_confirmation(self):
        self.edit_spec('risk_confirmed_by: "technical-lead"', 'risk_confirmed_by: ""')
        self.assertTrue(any("risk_confirmed_by" in x for x in self.p()))

    def test_data_class_above_tool_limit(self):
        self.edit_spec("data_class: internal", "data_class: personal")
        self.assertTrue(any("above the limit" in x for x in self.p()))

    def test_missing_acceptance_criteria(self):
        text = self.spec.read_text()
        self.spec.write_text("\n".join(l for l in text.splitlines() if "**AC" not in l))
        self.assertTrue(any("acceptance criteria" in x for x in self.p()))

    def test_template_values_fail(self):
        shutil.copy(self.tmp / "specs" / "_template" / "spec.md", self.spec)
        self.assertTrue(any("template value" in x for x in self.p()))

    def test_broken_front_matter(self):
        self.spec.write_text("---\nrisk_class: [unclosed\n---\n")
        self.assertTrue(any("not valid YAML" in x for x in self.p()))

    def exception(self, expiry):
        d = self.tmp / "governance" / "exceptions"
        d.mkdir(exist_ok=True)
        (d / "EXC-001-test.md").write_text(f"| Expiry or review date | {expiry} |\n")
        return "governance/exceptions/EXC-001-test.md"

    def test_restricted_without_exception_fails(self):
        self.edit_spec("risk_class: Elevated", "risk_class: Restricted")
        self.assertTrue(any("does not permit AI use" in x for x in self.p()))

    def test_restricted_with_valid_exception_passes(self):
        path = self.exception("2026-12-31")
        self.edit_spec("risk_class: Elevated", "risk_class: Restricted")
        self.assertEqual(self.p(GOOD_BODY.replace("Exception: none", f"Exception: {path}")), [])

    def test_expired_exception_fails(self):
        path = self.exception("2026-01-31")
        self.assertTrue(any("expired" in x for x in self.p(GOOD_BODY.replace("Exception: none", f"Exception: {path}"))))


if __name__ == "__main__":
    unittest.main()
