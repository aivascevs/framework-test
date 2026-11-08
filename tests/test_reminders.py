"""Tests for scripts/reminders.py."""
import datetime as dt
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import reminders as rm  # noqa: E402

TODAY = dt.date(2026, 10, 26)


class ReminderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / "governance", self.tmp / "governance")
        shutil.copytree(ROOT / "policy-config", self.tmp / "policy-config")
        (self.tmp / "governance" / "exceptions").mkdir(exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def exc(self, name, expiry, approver="Risk Owner, security lead"):
        (self.tmp / "governance" / "exceptions" / name).write_text(
            f"| Approved by | {approver} |\n| Expiry or review date | {expiry} |\n")

    def test_nothing_due_in_repository(self):
        self.assertEqual(rm.collect(self.tmp, TODAY, 14), [])

    def test_exception_due_soon_and_overdue(self):
        self.exc("EXC-001-a.md", "2026-11-02")
        self.exc("EXC-002-b.md", "2026-10-01")
        self.exc("EXC-003-c.md", "2027-06-01")
        items = rm.collect(self.tmp, TODAY, 14)
        self.assertEqual(len(items), 2)
        self.assertTrue(items[0].startswith("Due in 7 days"))
        self.assertTrue(items[1].startswith("**Overdue**"))

    def test_unapproved_draft(self):
        self.exc("EXC-001-a.md", "2027-01-01", approver="<name and role of the risk owner>")
        self.assertTrue(any("Not approved" in i for i in rm.collect(self.tmp, TODAY, 14)))

    def test_osv_override_due(self):
        osv = self.tmp / "policy-config" / "osv-scanner.toml"
        osv.write_text(osv.read_text() + '\n[[IgnoredVulns]]\nid = "GHSA-test-0000-0000"\n'
                       'ignoreUntil = 2026-11-01T00:00:00Z\nreason = "EXC-001: test"\n')
        self.assertTrue(any("GHSA-test-0000-0000" in i for i in rm.collect(self.tmp, TODAY, 14)))

    def test_tool_register_review_due(self):
        items = rm.collect(self.tmp, dt.date(2027, 4, 20), 14)
        self.assertTrue(any("tool register" in i for i in items), items)


if __name__ == "__main__":
    unittest.main()
