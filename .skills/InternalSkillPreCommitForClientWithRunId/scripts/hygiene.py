#!/usr/bin/env python3
"""Run the three receipt-hygiene checks of InternalSkillPreCommitForClientWithRunId.

Usage: .skills/InternalSkillPreCommitForClientWithRunId/scripts/hygiene.py   (from the repository root)
Output: a JSON array of {"check", "status", "detail"} objects, one per check;
"detail" is null unless the check fails.
Exit code: 0 when all checks pass, 1 when at least one fails.
"""
import json
import subprocess
import sys


def git(*args):
    try:
        proc = subprocess.run(["git", *args], capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        print(f"error: timeout: git {' '.join(args)} exceeded 120s", file=sys.stderr)
        sys.exit(1)
    return proc.returncode, proc.stdout.strip()


def main():
    checks = []

    code, _ = git("check-ignore", "-q", "tmp/probe")
    checks.append({
        "check": "tmp-gitignored",
        "status": "pass" if code == 0 else "fail",
        "detail": None if code == 0 else "the tmp/ directory is not gitignored",
    })

    _, tracked = git("ls-files", "--", "tmp/")
    checks.append({
        "check": "no-tracked-receipts",
        "status": "pass" if not tracked else "fail",
        "detail": None if not tracked else "tracked files under tmp/: " + ", ".join(tracked.splitlines()),
    })

    _, staged = git("diff", "--cached", "--name-only", "--", "tmp/")
    checks.append({
        "check": "no-staged-receipts",
        "status": "pass" if not staged else "fail",
        "detail": None if not staged else "staged files under tmp/: " + ", ".join(staged.splitlines()),
    })

    print(json.dumps(checks, indent=2))
    return 0 if all(c["status"] == "pass" for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
