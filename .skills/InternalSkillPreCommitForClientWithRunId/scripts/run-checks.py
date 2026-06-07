#!/usr/bin/env python3
"""Run the pre-commit checks extracted from a client repo's PRECOMMIT.md.

Usage: .skills/InternalSkillPreCommitForClientWithRunId/scripts/run-checks.py --checks-file PATH
       (from the repository root)

The runner reads the free-form PRECOMMIT.md, extracts each check as a
{"check", "directory", "command"} object, and writes the list as a JSON array
to PATH (typically tmp/<SkillRunId>-precommit-checks.json). This script runs
each command from its directory and reports the outcome — it does not parse
PRECOMMIT.md itself, because that interpretation is a judgment call left to the
runner.

Output: a JSON array of {"check", "status", "detail"} objects ("detail" is null
unless the check fails); an empty input array prints [].
Exit code: 0 when every check passes or the list is empty, 1 when at least one
check fails, 2 when the input cannot be read or is malformed.
"""
import argparse
import json
import os
import subprocess
import sys

REQUIRED = {"check", "directory", "command"}


def die(message):
    print(json.dumps({"error": message}))
    return 2


def run_check(entry):
    if not isinstance(entry, dict) or REQUIRED - set(entry):
        missing = REQUIRED - set(entry if isinstance(entry, dict) else {})
        return None, f"check entry is missing fields: {', '.join(sorted(missing))}"
    directory = entry["directory"]
    if not os.path.isdir(directory):
        return "fail", f"directory {directory!r} does not exist"
    proc = subprocess.run(
        entry["command"],
        shell=True,
        cwd=directory,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return "pass", None
    detail = proc.stderr.strip() or proc.stdout.strip() or f"exit code {proc.returncode}"
    if len(detail) > 500:
        detail = detail[:497] + "..."
    return "fail", f"{entry['command']!r} in {directory!r} failed: {detail}"


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--checks-file", required=True)
    args = parser.parse_args()

    if not os.path.isfile(args.checks_file):
        return die(f"checks file not found: {args.checks_file}")
    try:
        checks = json.load(open(args.checks_file))
    except json.JSONDecodeError as exc:
        return die(f"could not parse {args.checks_file}: {exc}")
    if not isinstance(checks, list):
        return die(f"{args.checks_file} must contain a JSON array")

    results = []
    for entry in checks:
        status, detail = run_check(entry)
        if status is None:
            return die(detail)
        name = entry["check"]
        results.append({"check": name, "status": status, "detail": detail})

    print(json.dumps(results, indent=2))
    return 0 if all(r["status"] == "pass" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
