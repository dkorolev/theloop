#!/usr/bin/env python3
"""Check that every maxims/ .md exactly matches its .yml source of truth.

Usage (from the repository root):
  check-maxims.py

The .yml files are the source of truth; each .md is generated from its .yml. This
verifies, and prints as JSON:
  - every category .yml listed in metadata.json is present (and none is present but
    unlisted),
  - a one-to-one mapping between the .yml and .md files (no orphan of either), and
  - each .md is byte-for-byte what `render-maxims.py` would generate from its .yml.

Output: {"status": "pass"|"fail", "issues": [...]} on stdout.
Exit code: 0 when consistent, 1 when any discrepancy is found.
"""
import json
import os
import sys

from common import MAXIMS_DIR, require_ready, read_metadata, load_category, render_md


def main():
    require_ready()
    declared = set(read_metadata().get("categories", []))
    ymls = {f for f in os.listdir(MAXIMS_DIR) if f.endswith(".yml")}
    mds = {f for f in os.listdir(MAXIMS_DIR) if f.endswith(".md")}
    issues = []

    for name in sorted(declared - ymls):
        issues.append({"file": name, "problem": "declared-missing",
                       "detail": f"metadata.json lists category {name} but it is not present in maxims/"})
    for name in sorted(ymls - declared):
        issues.append({"file": name, "problem": "undeclared-yml",
                       "detail": f"{name} is present but not listed in metadata.json categories"})

    yml_bases = {f[:-4] for f in ymls}
    md_bases = {f[:-3] for f in mds}
    for base in sorted(yml_bases - md_bases):
        issues.append({"file": base + ".yml", "problem": "missing-md",
                       "detail": f"{base}.yml has no generated {base}.md"})
    for base in sorted(md_bases - yml_bases):
        issues.append({"file": base + ".md", "problem": "orphan-md",
                       "detail": f"{base}.md has no {base}.yml source of truth"})

    for base in sorted(yml_bases & md_bases):
        expected = render_md(load_category(os.path.join(MAXIMS_DIR, base + ".yml")))
        with open(os.path.join(MAXIMS_DIR, base + ".md"), encoding="utf-8") as f:
            actual = f.read()
        if actual != expected:
            issues.append({"file": base + ".md", "problem": "out-of-sync",
                           "detail": f"{base}.md differs from `render-maxims.py maxims/{base}.yml`; "
                                     f"regenerate the .md from the .yml"})

    status = "pass" if not issues else "fail"
    print(json.dumps({"status": status, "issues": issues}, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
