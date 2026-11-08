#!/usr/bin/env python3
"""Check a package before an agent proposes or installs it (C5). Standard library only.

For each package the script asks the public registry:
  - Does the package exist?            (a model can invent package names; see "slopsquatting")
  - Does the requested version exist?
  - How old is the package?            (very new packages need a closer look)
  - Which licence does it declare?     (compared with policy-config/allowed-licenses.txt)

Usage:
    check_package.py pypi requests==2.32.3
    check_package.py npm zod@3.23.8
    check_package.py nuget Newtonsoft.Json@13.0.3
    check_package.py pypi some-name --json

Exit codes: 0 all checks passed, 1 at least one finding, 2 usage or network error.
A pass does not prove that a package is safe. It is an input for the plan and the human review.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from xml.etree import ElementTree

MIN_AGE_DAYS = 90
TIMEOUT = 15
ROOT = Path(__file__).resolve().parents[4]
ALLOWLIST = ROOT / "policy-config" / "allowed-licenses.txt"


class NotFound(Exception):
    pass


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "governance-dependency-check/1.0",
                                               "Accept-Encoding": "gzip"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = r.read()
            if r.headers.get("Content-Encoding") == "gzip" or data[:2] == b"\x1f\x8b":
                data = gzip.decompress(data)
            return data
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise NotFound(url) from e
        raise


def parse_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


# ------------------------------------------------------------------ registries
CLASSIFIER_SPDX = {  # common PyPI licence classifiers and free-text values -> SPDX
    "mit license": "MIT", "mit": "MIT",
    "apache software license": "Apache-2.0", "apache 2.0": "Apache-2.0", "apache-2.0": "Apache-2.0",
    "apache license 2.0": "Apache-2.0", "apache license, version 2.0": "Apache-2.0",
    "isc license (iscl)": "ISC", "python software foundation license": "PSF-2.0",
    "gnu general public license v3 (gplv3)": "GPL-3.0-only", "gpl v3": "GPL-3.0-only",
    "gnu general public license v2 (gplv2)": "GPL-2.0-only",
    "gnu lesser general public license v2 or later (lgplv2+)": "LGPL-2.1-or-later",
    "gnu lesser general public license v3 (lgplv3)": "LGPL-3.0-only",
    "mozilla public license 2.0 (mpl 2.0)": "MPL-2.0", "the unlicense (unlicense)": "Unlicense",
}


def to_spdx(value: str) -> str:
    return CLASSIFIER_SPDX.get(value.strip().lower(), value.strip())


def advisories(ecosystem: str, name: str, version: str | None) -> list[str] | None:
    """Known advisory IDs from OSV.dev for one version. None when the lookup was not possible."""
    if not version:
        return []
    body = json.dumps({"package": {"name": name, "ecosystem": ecosystem}, "version": version}).encode()
    req = urllib.request.Request("https://api.osv.dev/v1/query", data=body,
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "governance-dependency-check/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            vulns = json.loads(r.read() or b"{}").get("vulns", [])
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None
    return sorted(v.get("id", "?") for v in vulns)


def pypi(name: str, version: str | None) -> dict:
    data = json.loads(fetch(f"https://pypi.org/pypi/{name}/json"))
    info, releases = data["info"], data.get("releases", {})
    dates = [parse_date(f.get("upload_time_iso_8601")) for files in releases.values() for f in files]
    dates = [d for d in dates if d]
    licence = info.get("license_expression") or ""
    if not licence:
        classifiers = [to_spdx(c.split("::")[-1]) for c in info.get("classifiers", []) if c.startswith("License ::")]
        classifiers = [c for c in classifiers if c != "OSI Approved"]
        licence = " OR ".join(classifiers) if classifiers else to_spdx((info.get("license") or "")[:60])
    return {"name": info["name"], "latest": info["version"], "versions": set(releases),
            "first_release": min(dates) if dates else None, "licence": licence.strip()}


def npm(name: str, version: str | None) -> dict:
    data = json.loads(fetch(f"https://registry.npmjs.org/{name}"))
    times = data.get("time", {})
    latest = data.get("dist-tags", {}).get("latest")
    meta = data.get("versions", {}).get(version or latest, {})
    licence = meta.get("license") or data.get("license") or ""
    if isinstance(licence, dict):
        licence = licence.get("type", "")
    return {"name": data.get("name", name), "latest": latest, "versions": set(data.get("versions", {})),
            "first_release": parse_date(times.get("created")), "licence": str(licence)}


def nuget(name: str, version: str | None) -> dict:
    low = name.lower()
    versions = json.loads(fetch(f"https://api.nuget.org/v3-flatcontainer/{low}/index.json"))["versions"]
    latest = versions[-1] if versions else None
    reg = json.loads(fetch(f"https://api.nuget.org/v3/registration5-gz-semver2/{low}/index.json"))
    published = []
    for page in reg.get("items", []):
        for item in page.get("items", []):
            d = parse_date(item.get("catalogEntry", {}).get("published"))
            if d and d.year > 1900:
                published.append(d)
    nuspec = fetch(f"https://api.nuget.org/v3-flatcontainer/{low}/{(version or latest).lower()}/{low}.nuspec")
    root = ElementTree.fromstring(nuspec)
    lic = next((el.text for el in root.iter() if el.tag.endswith("license") and el.text), "")
    if not lic:
        lic = next((f"licenseUrl: {el.text}" for el in root.iter() if el.tag.endswith("licenseUrl") and el.text), "")
    return {"name": name, "latest": latest, "versions": set(versions),
            "first_release": min(published) if published else None, "licence": lic.strip()}


REGISTRIES = {"pypi": (pypi, "=="), "npm": (npm, "@"), "nuget": (nuget, "@")}
OSV_ECOSYSTEM = {"pypi": "PyPI", "npm": "npm", "nuget": "NuGet"}


# ------------------------------------------------------------------ checks
def allowed_licences(path: Path = ALLOWLIST) -> set[str]:
    if not path.is_file():
        return set()
    return {l.strip() for l in path.read_text().splitlines() if l.strip() and not l.strip().startswith("#")}


def licence_ok(expr: str, allowed: set[str]) -> bool | None:
    """True / False for SPDX ids and simple OR / AND expressions. None when the value is not SPDX."""
    if not expr:
        return None
    parts_or = [p.strip(" ()") for p in re.split(r"\s+OR\s+", expr)]
    if all(re.fullmatch(r"[A-Za-z0-9.+-]+(\s+AND\s+[A-Za-z0-9.+-]+)*", p) for p in parts_or):
        return any(all(a.strip() in allowed for a in p.split(" AND ")) for p in parts_or)
    return None


def check(registry: str, spec: str, today: dt.date | None = None, allowed: set[str] | None = None,
          lookup=None, advisory_lookup=None) -> dict:
    func, sep = REGISTRIES[registry]
    name, _, version = spec.partition(sep) if not spec.startswith("@") or sep == "==" else \
        ("@" + spec[1:].partition("@")[0], "@", spec[1:].partition("@")[2])
    version = version or None
    today = today or dt.date.today()
    allowed = allowed if allowed is not None else allowed_licences()
    findings: list[str] = []
    try:
        meta = (lookup or func)(name, version)
    except NotFound:
        return {"package": spec, "registry": registry, "exists": False,
                "findings": [f"Package '{name}' does not exist on {registry}. The name may be invented. "
                             "Do not install it. Check the spelling and the official documentation."]}
    if version and version not in meta["versions"]:
        findings.append(f"Version {version} does not exist. Latest is {meta['latest']}.")
    age = (today - meta["first_release"]).days if meta["first_release"] else None
    if age is not None and age < MIN_AGE_DAYS:
        findings.append(f"Package first released {age} days ago (< {MIN_AGE_DAYS}). Ask a human to check it.")
    vulns = (advisory_lookup or advisories)(OSV_ECOSYSTEM[registry], meta["name"], version) \
        if version and version in meta["versions"] else []
    if vulns is None:
        notes = ["Known advisories not checked: OSV.dev was not reachable. CI checks them again."]
    else:
        notes = []
        if vulns:
            findings.append(f"Version {version} has {len(vulns)} known advisory(ies): {', '.join(vulns[:5])}. "
                            "Choose a fixed version.")
    ok = licence_ok(meta["licence"], allowed)
    if ok is False:
        findings.append(f"Licence '{meta['licence']}' is not in policy-config/allowed-licenses.txt. "
                        "A human decides (exception record).")
    elif ok is None:
        findings.append(f"Licence '{meta['licence'] or 'not declared'}' is not an SPDX identifier. Ask a human to check it.")
    return {"package": spec, "registry": registry, "exists": True, "latest": meta["latest"],
            "first_release": str(meta["first_release"]) if meta["first_release"] else None,
            "age_days": age, "licence": meta["licence"], "advisories": vulns, "notes": notes,
            "findings": findings}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("registry", choices=sorted(REGISTRIES))
    ap.add_argument("packages", nargs="+", help="name, name==version (pypi) or name@version (npm, nuget)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    results, error = [], False
    for spec in args.packages:
        try:
            results.append(check(args.registry, spec))
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as e:
            results.append({"package": spec, "registry": args.registry, "error": f"not checked: {e}"})
            error = True
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            if "error" in r:
                print(f"{r['package']}: {r['error']}")
                continue
            status = ("FINDINGS" if r["findings"] else
                      "no findings, advisories NOT checked" if r.get("advisories") is None and r["exists"] else
                      "ok")
            extra = f" licence={r.get('licence') or '-'} first_release={r.get('first_release')}" if r["exists"] else ""
            print(f"{r['package']} ({r['registry']}): {status}{extra}")
            for f in r["findings"]:
                print(f"  - {f}")
            for n in r.get("notes", []):
                print(f"  note: {n}")
    if error:
        return 2
    return 1 if any(r.get("findings") for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
