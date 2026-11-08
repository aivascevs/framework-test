"""Tests for the scripts bundled with skills, the Claude Code hooks and the agent-config check.
No network access: registries and OSV.dev are replaced by stubs. All data is synthetic.
"""
import datetime as dt
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


scan = load("scan_sensitive", ".claude/skills/sensitive-data-guard/scripts/scan_sensitive.py")
pkg = load("check_package", ".claude/skills/dependency-check/scripts/check_package.py")
scope = load("scope_guard", ".claude/hooks/scope_guard.py")
import check_agent_config as cac  # noqa: E402

# Synthetic values. A provider-shaped token is assembled at run time, so the file holds no token.
AWS_LIKE = "AKIA" + "EXAMPLE0" + "TESTONLY"
MAIL = "ana.berzina" + "@" + "corp-mail" + ".lv"   # invented address, built at run time
TODAY = dt.date(2026, 10, 26)


class ScannerTests(unittest.TestCase):
    def rules(self, text):
        return [f.rule for f in scan.scan_text(text, "x.py")]

    def test_finds_secret_and_never_prints_value(self):
        findings = scan.scan_text(f'key = "{AWS_LIKE}"', "x.py")
        self.assertIn("aws-access-key-id", [f.rule for f in findings])
        self.assertTrue(all(AWS_LIKE not in f.hint for f in findings))

    def test_personal_data_with_validators(self):
        self.assertIn("email-address", self.rules(f"contact {MAIL}"))
        self.assertEqual(self.rules("contact ana@example.test"), [])          # reserved test domain
        self.assertIn("payment-card", self.rules("card 4111 1111 1111 1111"))  # sensitive-data: synthetic
        self.assertNotIn("payment-card", self.rules("card 4111 1111 1111 1112"))   # Luhn fails
        self.assertIn("iban", self.rules("GB82 WEST 1234 5698 7654 32"))  # sensitive-data: synthetic
        self.assertIn("lv-personal-code", self.rules("code 120380-12305"))  # sensitive-data: synthetic

    def test_package_spec_is_not_an_email(self):
        self.assertEqual(self.rules("npx @mermaid-js/mermaid-cli@12.0.0"), [])

    def test_synthetic_marker_skips_line(self):
        self.assertEqual(self.rules(f"{MAIL}  # sensitive-data: synthetic"), [])

    def test_stdin_exit_codes(self):
        with mock.patch("sys.stdin", io.StringIO("nothing here\n")), mock.patch("sys.stdout", io.StringIO()):
            self.assertEqual(scan.main(["--stdin"]), 0)
        with mock.patch("sys.stdin", io.StringIO(f"mail {MAIL}\n")), \
                mock.patch("sys.stdout", io.StringIO()) as out:
            self.assertEqual(scan.main(["--stdin"]), 1)
        self.assertNotIn(MAIL, out.getvalue())


def meta(first_release=dt.date(2020, 1, 1), licence="MIT", versions=("1.0.0", "1.1.0")):
    return {"name": "examplepkg", "latest": versions[-1], "versions": set(versions),
            "first_release": first_release, "licence": licence}


class PackageTests(unittest.TestCase):
    allowed = {"MIT", "Apache-2.0", "BSD-3-Clause"}

    def run_check(self, spec="examplepkg==1.1.0", registry="pypi", m=None, adv=lambda *a: []):
        lookup = (lambda n, v: m) if not isinstance(m, Exception) else mock.Mock(side_effect=m)
        return pkg.check(registry, spec, TODAY, self.allowed, lookup=lookup, advisory_lookup=adv)

    def test_clean_package(self):
        self.assertEqual(self.run_check(m=meta())["findings"], [])

    def test_invented_package(self):
        r = self.run_check(m=pkg.NotFound("x"))
        self.assertFalse(r["exists"])
        self.assertIn("may be invented", r["findings"][0])

    def test_missing_version(self):
        self.assertIn("does not exist", self.run_check("examplepkg==9.9.9", m=meta())["findings"][0])

    def test_new_package(self):
        r = self.run_check(m=meta(first_release=TODAY - dt.timedelta(days=10)))
        self.assertTrue(any("days ago" in f for f in r["findings"]))

    def test_licence_outside_allowlist(self):
        self.assertTrue(any("not in policy-config" in f for f in self.run_check(m=meta(licence="GPL-3.0-only"))["findings"]))

    def test_licence_or_expression(self):
        self.assertEqual(self.run_check(m=meta(licence="GPL-2.0-only OR MIT"))["findings"], [])

    def test_non_spdx_licence(self):
        self.assertTrue(any("not an SPDX" in f for f in self.run_check(m=meta(licence="Custom terms"))["findings"]))

    def test_advisories(self):
        r = self.run_check(m=meta(), adv=lambda *a: ["GHSA-test-0000-0000"])
        self.assertTrue(any("known advisory" in f for f in r["findings"]))

    def test_advisories_unreachable_is_a_note(self):
        r = self.run_check(m=meta(), adv=lambda *a: None)
        self.assertEqual(r["findings"], [])
        self.assertTrue(r["notes"])

    def test_scoped_npm_name(self):
        seen = {}

        def lookup(name, version):
            seen["name"], seen["version"] = name, version
            return meta(licence="MIT")
        pkg.check("npm", "@scope/examplepkg@1.1.0", TODAY, self.allowed, lookup=lookup, advisory_lookup=lambda *a: [])
        self.assertEqual(seen, {"name": "@scope/examplepkg", "version": "1.1.0"})

    def test_nuget_parser_with_stubbed_registry(self):
        responses = {
            "index.json": json.dumps({"versions": ["1.0.0", "2.0.0"]}).encode(),
            "registration": json.dumps({"items": [{"items": [
                {"catalogEntry": {"published": "2019-05-01T00:00:00Z"}},
                {"catalogEntry": {"published": "1900-01-01T00:00:00Z"}}]}]}).encode(),
            "nuspec": b'<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">'
                      b'<metadata><license type="expression">Apache-2.0</license></metadata></package>',
        }

        def fake_fetch(url):
            key = "registration" if "registration" in url else "nuspec" if url.endswith(".nuspec") else "index.json"
            return responses[key]
        with mock.patch.object(pkg, "fetch", fake_fetch):
            m = pkg.nuget("Example.Package", "2.0.0")
        self.assertEqual(m["licence"], "Apache-2.0")
        self.assertEqual(m["first_release"], dt.date(2019, 5, 1))
        self.assertEqual(m["latest"], "2.0.0")


class ScopeHookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / "specs", self.tmp / "specs")
        shutil.copytree(ROOT / "policy-config", self.tmp / "policy-config")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def decide(self, rel):
        return scope.decide({"tool_input": {"file_path": str(self.tmp / rel)}}, self.tmp)[0]

    def write_event(self, rel, n_lines):
        return {"tool_name": "Write", "tool_input": {"file_path": str(self.tmp / rel),
                                                     "content": "x = 1\n" * n_lines}}

    def set_spec(self, extra_files="", generated="none", increments=""):
        spec = self.tmp / "specs/001-sample-change/spec.md"
        text = spec.read_text()
        if extra_files:
            text = text.replace("`sample-app/tests/test_store.py` |", f"`sample-app/tests/test_store.py`, {extra_files} |", 1)
        text = text.replace("| Generated files | none |", f"| Generated files | {generated} |", 1)
        if increments:
            start, end = text.index("## 8. Increments"), text.index("## 9. Open questions")
            text = text[:start] + increments + text[end:]
        spec.write_text(text)

    def test_no_active_spec_permits(self):
        self.assertEqual(self.decide("governance/policy.md"), 0)

    def test_active_spec_limits_edits(self):
        (self.tmp / ".active-spec").write_text("specs/001-sample-change/spec.md\n")
        self.assertEqual(self.decide("sample-app/orders/store.py"), 0)
        self.assertEqual(self.decide("specs/001-sample-change/plan.md"), 0)
        self.assertEqual(self.decide("governance/policy.md"), 2)

    def test_increment_narrows_scope(self):
        self.set_spec(increments="## 8. Increments (C9)\n\n| ID | R | Files | E | D | S |\n|---|---|---|---|---|---|\n"
                                 "| INC-1 | a | `sample-app/orders/store.py` | ~50 | — | planned |\n"
                                 "| INC-2 | b | `sample-app/tests/test_store.py` | ~50 | INC-1 | planned |\n\n")
        (self.tmp / ".active-spec").write_text("specs/001-sample-change/spec.md\nINC-1\n")
        self.assertEqual(self.decide("sample-app/orders/store.py"), 0)
        self.assertEqual(self.decide("sample-app/tests/test_store.py"), 2)

    def test_large_new_file_blocked(self):
        self.set_spec(extra_files="`sample-app/orders/*.py`")
        (self.tmp / ".active-spec").write_text("specs/001-sample-change/spec.md\n")
        code, msg = scope.decide(self.write_event("sample-app/orders/big.py", 301), self.tmp)
        self.assertEqual(code, 2)
        self.assertIn("C9", msg)
        self.assertEqual(scope.decide(self.write_event("sample-app/orders/ok.py", 300), self.tmp)[0], 0)

    def test_large_generated_file_permitted(self):
        self.set_spec(generated="`sample-app/orders/rates_gen.py` — produced by `python gen.py`")
        (self.tmp / ".active-spec").write_text("specs/001-sample-change/spec.md\n")
        self.assertEqual(scope.decide(self.write_event("sample-app/orders/rates_gen.py", 5000), self.tmp)[0], 0)

    def test_outside_repository_blocks(self):
        (self.tmp / ".active-spec").write_text("specs/001-sample-change/spec.md\n")
        code, _ = scope.decide({"tool_input": {"file_path": "/etc/hosts"}}, self.tmp)
        self.assertEqual(code, 2)


class AgentConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for part in (".claude/agents", ".vscode", "policy-config"):
            shutil.copytree(ROOT / part, self.tmp / part)
        shutil.copy(ROOT / ".claude/settings.json", self.tmp / ".claude/settings.json")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def edit(self, rel, old, new):
        p = self.tmp / rel
        text = p.read_text()
        self.assertIn(old, text)
        p.write_text(text.replace(old, new, 1))

    def test_repository_config_passes(self):
        self.assertEqual(cac.check(self.tmp), [])

    def test_sandbox_off_fails(self):
        self.edit(".claude/settings.json", '"enabled": true', '"enabled": false')
        self.assertTrue(any("sandbox.enabled" in p for p in cac.check(self.tmp)))

    def test_plan_mode_removed_fails(self):
        self.edit(".claude/settings.json", '"defaultMode": "plan"', '"defaultMode": "acceptEdits"')
        self.assertTrue(any("defaultMode" in p for p in cac.check(self.tmp)))

    def test_broad_allow_fails(self):
        self.edit(".claude/settings.json", '"Bash(git status)"', '"Bash(*)"')
        self.assertTrue(any("too broad" in p for p in cac.check(self.tmp)))

    def test_extra_domain_fails(self):
        self.edit(".claude/settings.json", '"api.osv.dev"', '"api.osv.dev", "paste.example.test"')
        self.assertTrue(any("paste.example.test" in p for p in cac.check(self.tmp)))

    def test_vscode_auto_approve_push_fails(self):
        self.edit(".vscode/settings.json", '"/^git push\\\\b/": false', '"/^git push\\\\b/": true')
        p = cac.check(self.tmp)
        self.assertTrue(any("git push" in x for x in p), p)

    def test_reviewer_with_edit_tool_fails(self):
        self.edit(".claude/agents/reviewer.md", "tools: Read, Grep, Glob", "tools: Read, Grep, Glob, Edit")
        self.assertTrue(any("read-only" in p for p in cac.check(self.tmp)))

    def test_mcp_file_fails(self):
        (self.tmp / ".mcp.json").write_text("{}")
        self.assertTrue(any(".mcp.json" in p for p in cac.check(self.tmp)))

    def test_jsonc_strip_keeps_strings(self):
        self.assertEqual(json.loads(cac.strip_jsonc('{"a": "x // y", // c\n "b": 1,}')), {"a": "x // y", "b": 1})


if __name__ == "__main__":
    unittest.main()
