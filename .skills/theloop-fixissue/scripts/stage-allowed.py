#!/usr/bin/env python3
"""Stage all changes except the paths listed in .theloop/do_not_commit.txt.

Usage: .skills/theloop-fixissue/scripts/stage-allowed.py   (from the repository root)

Runs `git add -A`, then unstages every path listed in .theloop/do_not_commit.txt
(plain paths, one per line; blank lines and lines starting with # are ignored).
It then asserts that no excluded path remains staged, so theloop instrumentation
can never land in a feature commit. When .theloop/do_not_commit.txt is absent — as
in the theloop repository itself — it stages everything, the previous behavior.

Output: a JSON object {"staged", "excluded"} on stdout, listing the staged paths
and the exclusion prefixes that were applied.
Exit code: 0 on success, 1 on error (including an excluded path left staged).
"""
import json
import os
import subprocess
import sys
from typing import NoReturn

DO_NOT_COMMIT = os.path.join(".theloop", "do_not_commit.txt")


def die(message) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def git(*args):
    proc = subprocess.run(["git", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        die((proc.stderr or proc.stdout or f"git {' '.join(args)} failed").strip())
    return proc.stdout


def read_exclusions():
    if not os.path.isfile(DO_NOT_COMMIT):
        return []
    paths = []
    for raw in open(DO_NOT_COMMIT):
        line = raw.strip()
        if line and not line.startswith("#"):
            paths.append(line.rstrip("/"))
    return paths


def is_under(path, prefix):
    return path == prefix or path.startswith(prefix + "/")


def main():
    exclusions = read_exclusions()
    git("add", "-A")
    for prefix in exclusions:
        git("reset", "-q", "--", prefix)

    staged = [p for p in git("diff", "--cached", "--name-only").splitlines() if p]
    leaked = [p for p in staged if any(is_under(p, e) for e in exclusions)]
    if leaked:
        die("excluded paths are still staged: " + ", ".join(leaked))

    print(json.dumps({"staged": staged, "excluded": exclusions}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
