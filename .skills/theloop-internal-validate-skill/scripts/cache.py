#!/usr/bin/env python3
"""Probe and write the validation cache of theloop-internal-validate-skill, per .theloop/CACHING.md.

Usage: .skills/theloop-internal-validate-skill/scripts/cache.py probe <SkillNameToCheck>   (from the repository root)
       .skills/theloop-internal-validate-skill/scripts/cache.py write <SkillNameToCheck>
The input set is every non-ignored file under .skills/<SkillNameToCheck>/ plus
.theloop/SKILLS-META-RULES.md, SKILLS.md, and .theloop/VIZ.md; the check name is
"theloop-internal-validate-skill:<SkillNameToCheck>".
Output of probe: one JSON object {"check", "fingerprint", "cached", "cache_path"} on stdout.
Output of write: the path of the written cache entry on stdout (written only after
a passing verdict; idempotent when the entry already exists).
Exit code: 0 on success, 2 when the target skill does not exist or the usage is
wrong (then {"error": ...} is printed).
"""
import hashlib
import json
import os
import subprocess
import sys

EXTRA_FILES = [os.path.join(".theloop", "SKILLS-META-RULES.md"), "SKILLS.md", os.path.join(".theloop", "VIZ.md")]
CACHE_DIR = os.path.join("tmp", "caches")


def sha256_of(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def manifest_of(skill):
    try:
        listed = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", f".skills/{skill}/"],
            capture_output=True, text=True, check=True, timeout=120,
        ).stdout.splitlines()
    except subprocess.TimeoutExpired:
        print(json.dumps({"error": "timeout: git ls-files exceeded 120s"}))
        sys.exit(2)
    paths = sorted(p for p in set(listed) | set(EXTRA_FILES) if os.path.isfile(p))
    check = f"theloop-internal-validate-skill:{skill}"
    lines = [f"{sha256_of(p)}  {p}" for p in paths]
    return check, f"check: {check}\n" + "".join(line + "\n" for line in lines), lines


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("probe", "write"):
        print(json.dumps({"error": "usage: cache.py probe|write <SkillNameToCheck>"}))
        return 2
    action, skill = sys.argv[1], sys.argv[2]
    if not os.path.isfile(f".skills/{skill}/SKILL.md"):
        print(json.dumps({"error": f".skills/{skill}/SKILL.md not found: no such skill"}))
        return 2

    check, manifest, lines = manifest_of(skill)
    fingerprint = hashlib.sha256(manifest.encode("utf-8")).hexdigest()
    cache_path = os.path.join(CACHE_DIR, fingerprint + ".txt")

    if action == "probe":
        print(json.dumps({
            "check": check,
            "fingerprint": fingerprint,
            "cached": os.path.isfile(cache_path),
            "cache_path": cache_path,
        }, indent=2))
        return 0

    os.makedirs(CACHE_DIR, exist_ok=True)
    if not os.path.isfile(cache_path):
        with open(cache_path, "w") as f:
            f.write(f"check: {check}\nverdict: pass\nfiles:\n" + "".join(line + "\n" for line in lines))
    print(cache_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
