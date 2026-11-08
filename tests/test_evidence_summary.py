"""Tests for scripts/evidence_summary.py."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import evidence_summary as es  # noqa: E402

META = {"values": {"Specification": "specs/001-sample-change/spec.md", "Risk class": "Elevated",
                   "AI use": "edit", "AI tool": "claude-code", "Capability profile": "P1",
                   "Exception": "none"}, "problems": []}
NEEDS = {"metadata": {"result": "success"}, "secrets": {"result": "failure"},
         "dependencies": {"result": "success"}, "tests-sast": {"result": "skipped"}}


class EvidenceTests(unittest.TestCase):
    def test_build_links_results_to_commit(self):
        e = es.build(META, NEEDS, {"PR_HEAD_SHA": "abc123", "GITHUB_REPOSITORY": "o/r", "PR_NUMBER": "7"})
        self.assertEqual(e["commit"], "abc123")
        self.assertEqual({c["job"]: c["result"] for c in e["checks"]}["secrets"], "failure")
        self.assertEqual(e["metadata"]["Risk class"], "Elevated")

    def test_missing_job_is_reported_as_not_run(self):
        e = es.build(META, {}, {})
        self.assertTrue(all(c["result"] == "not run" for c in e["checks"]))

    def test_markdown_states_what_is_not_included(self):
        md = es.to_markdown(es.build(META, NEEDS, {}))
        self.assertIn("Raw prompts", md)
        self.assertIn("| Secrets and personal data (gitleaks, sensitive-data patterns) | C3, C4 | failure |", md)
        self.assertIn("No guardrail findings", md)

    def test_review_items_from_guardrails(self):
        guard = {"minimum_class": "Elevated", "review": [
            {"check": "tests-removed", "message": "1 test file(s) deleted", "files": []},
            {"check": "scope", "message": "1 changed file(s) outside", "files": [],
             "accepted_by": "governance/exceptions/EXC-001-x.md"}]}
        e = es.build(META, NEEDS, {}, guard)
        self.assertEqual([r["check"] for r in e["review_items"]], ["tests-removed", "scope"])
        md = es.to_markdown(e)
        self.assertIn("Minimum risk class for the changed paths: Elevated", md)
        self.assertIn("(accepted by governance/exceptions/EXC-001-x.md)", md)

    def test_main_writes_both_files(self):
        with tempfile.TemporaryDirectory() as d:
            meta = Path(d, "metadata.json")
            meta.write_text(json.dumps(META))
            with mock.patch.dict(os.environ, {"NEEDS_JSON": json.dumps(NEEDS)}, clear=False), \
                    mock.patch("builtins.print"):
                self.assertEqual(es.main(["--metadata", str(meta), "--out-dir", d]), 0)
            self.assertTrue(Path(d, "evidence-summary.md").is_file())
            self.assertEqual(json.loads(Path(d, "evidence-summary.json").read_text())["metadata"]["AI tool"],
                             "claude-code")


if __name__ == "__main__":
    unittest.main()
