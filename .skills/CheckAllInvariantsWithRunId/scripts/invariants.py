#!/usr/bin/env python3
"""Check the invariant registry and enumerate invariants, per .ai/INVARIANTS.md.

Usage: .skills/CheckAllInvariantsWithRunId/scripts/invariants.py probe   (from the repository root)
probe checks that ai-invariants.yml lists exactly the non-ignored *-INVARIANT.md
files of the repository, fingerprints every invariant's directory subtree per
.ai/CACHING.md under the check name "invariant:<path-to-INVARIANT.md>", and reports
the registry status and the full list of invariants, each with its sub_run_suffix.
The sub_run_suffix for an invariant is its path with '/' replaced by '-' and the
'.md' suffix stripped; it is appended to the caller's SkillRunId to form the
sub-run identifier passed to CheckSingleInvariantWithRunId.
Output: one JSON object {"registry", "invariants"} on stdout, where "registry" is
{"status", "detail"} and each invariant is {"invariant", "directory", "sub_run_suffix",
"check", "fingerprint", "cached", "cache_path"}.
Exit code: 0 on success, 1 when the registry check fails, 2 on wrong usage.
"""
import hashlib
import json
import os
import subprocess
import sys

REGISTRY = "ai-invariants.yml"
CACHE_DIR = os.path.join("tmp", "caches")


def non_ignored_files(pathspec=None):
    cmd = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
    if pathspec is not None:
        cmd += ["--", pathspec]
    listed = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.splitlines()
    return sorted(p for p in set(listed) if os.path.isfile(p))


def registered_invariants():
    """Parse ai-invariants.yml: a flat YAML list of paths ('- <path>' lines, or '[]')."""
    if not os.path.isfile(REGISTRY):
        return None
    invariants = []
    for line in open(REGISTRY):
        line = line.split("#", 1)[0].strip()
        if not line or line == "[]":
            continue
        if not line.startswith("- "):
            raise ValueError(f"{REGISTRY} is not a flat YAML list of paths: unexpected line {line!r}")
        invariants.append(line[2:].strip())
    return invariants


def fingerprint_of(invariant):
    check = f"invariant:{invariant}"
    directory = os.path.dirname(invariant)
    paths = non_ignored_files(directory if directory else ".")
    lines = [f"{hashlib.sha256(open(p, 'rb').read()).hexdigest()}  {p}" for p in paths]
    manifest = f"check: {check}\n" + "".join(line + "\n" for line in lines)
    return check, directory or ".", hashlib.sha256(manifest.encode("utf-8")).hexdigest(), lines


def sub_run_suffix(invariant_path):
    """Deterministic sub-run suffix: replace '/' with '-' and strip '.md'."""
    return invariant_path.replace("/", "-").removesuffix(".md")


def main():
    if len(sys.argv) != 2 or sys.argv[1] != "probe":
        print(json.dumps({"error": "usage: invariants.py probe"}))
        return 2

    actual = [p for p in non_ignored_files() if p.endswith("-INVARIANT.md")]

    try:
        registered = registered_invariants()
    except ValueError as exc:
        print(json.dumps({"registry": {"status": "fail", "detail": str(exc)}, "invariants": []}, indent=2))
        return 1

    problems = []
    if registered is None:
        registered = []
        if actual:
            problems.append(f"{REGISTRY} does not exist, but the repo contains invariants: " + ", ".join(actual))
    else:
        for stale in sorted(set(registered) - set(actual)):
            problems.append(f"{REGISTRY} lists {stale}, which is not a non-ignored *-INVARIANT.md file of the repo")
        for missing in sorted(set(actual) - set(registered)):
            problems.append(f"{missing} is missing from {REGISTRY}")

    invariants = []
    for inv in sorted(set(registered) & set(actual)):
        check, directory, fingerprint, _ = fingerprint_of(inv)
        cache_path = os.path.join(CACHE_DIR, fingerprint + ".txt")
        invariants.append({
            "invariant": inv,
            "directory": directory,
            "sub_run_suffix": sub_run_suffix(inv),
            "check": check,
            "fingerprint": fingerprint,
            "cached": os.path.isfile(cache_path),
            "cache_path": cache_path,
        })

    print(json.dumps({
        "registry": {"status": "fail" if problems else "pass",
                     "detail": "; ".join(problems) if problems else None},
        "invariants": invariants,
    }, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
