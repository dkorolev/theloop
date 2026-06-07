#!/usr/bin/env python3
"""Probe and write the cache for a single directory invariant, per .ai/INVARIANTS.md.

Usage: .skills/CheckSingleInvariantWithRunId/scripts/invariants.py probe-one <path-to-INVARIANT.md>
       .skills/CheckSingleInvariantWithRunId/scripts/invariants.py write <path-to-INVARIANT.md>
probe-one fingerprints the invariant's directory subtree per .ai/CACHING.md under
the check name "invariant:<path-to-INVARIANT.md>" and reports whether a cache entry
exists for that fingerprint.
Output of probe-one: one JSON object {"invariant", "cached", "cache_path",
"fingerprint"} on stdout.
write writes the cache entry of the invariant, only to be called after the invariant
passed; idempotent when the entry already exists, prints its path.
Exit code: 0 on success, 2 on wrong usage or nonexistent invariant ({"error": ...} printed).
"""
import hashlib
import json
import os
import subprocess
import sys

CACHE_DIR = os.path.join("tmp", "caches")


def non_ignored_files(pathspec=None):
    cmd = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
    if pathspec is not None:
        cmd += ["--", pathspec]
    listed = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.splitlines()
    return sorted(p for p in set(listed) if os.path.isfile(p))


def fingerprint_of(invariant):
    check = f"invariant:{invariant}"
    directory = os.path.dirname(invariant)
    paths = non_ignored_files(directory if directory else ".")
    lines = [f"{hashlib.sha256(open(p, 'rb').read()).hexdigest()}  {p}" for p in paths]
    manifest = f"check: {check}\n" + "".join(line + "\n" for line in lines)
    return check, directory or ".", hashlib.sha256(manifest.encode("utf-8")).hexdigest(), lines


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("probe-one", "write"):
        print(json.dumps({"error": "usage: invariants.py probe-one <path> | invariants.py write <path>"}))
        return 2
    if len(sys.argv) != 3:
        print(json.dumps({"error": f"usage: invariants.py {sys.argv[1]} <path-to-INVARIANT.md>"}))
        return 2

    invariant = sys.argv[2]
    actual = [p for p in non_ignored_files() if p.endswith("-INVARIANT.md")]
    if invariant not in actual:
        print(json.dumps({"error": f"{invariant} is not a non-ignored *-INVARIANT.md file of this repository"}))
        return 2

    check, _, fingerprint, lines = fingerprint_of(invariant)
    cache_path = os.path.join(CACHE_DIR, fingerprint + ".txt")

    if sys.argv[1] == "probe-one":
        print(json.dumps({
            "invariant": invariant,
            "cached": os.path.isfile(cache_path),
            "cache_path": cache_path,
            "fingerprint": fingerprint,
        }, indent=2))
        return 0

    # write
    os.makedirs(CACHE_DIR, exist_ok=True)
    if not os.path.isfile(cache_path):
        with open(cache_path, "w") as f:
            f.write(f"check: {check}\nverdict: pass\nfiles:\n" + "".join(line + "\n" for line in lines))
    print(cache_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
