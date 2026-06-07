#!/usr/bin/env python3
"""Run the checks listed in PRECOMMIT.md.

Usage: .skills/PreCommitSkillWithRunId/scripts/precommit.py   (from the repository root)
If PRECOMMIT.md does not exist, prints null on stdout and exits 0.
Otherwise reads the YAML list in PRECOMMIT.md (inside a ```yaml fenced block, or the
whole file when no fence is present), runs each command from its directory, and prints
the outcomes as JSON.
Output: null when PRECOMMIT.md is absent; otherwise a JSON array of {"check", "status",
"detail"} objects ("detail" is null unless the check fails).
Exit code: 0 when every check passes or the file is absent, 1 when at least one check
fails, 2 when PRECOMMIT.md exists but cannot be parsed.
"""
import json
import os
import re
import subprocess
import sys

PRECOMMIT = "PRECOMMIT.md"
REQUIRED = {"check", "directory", "command"}


def die(message):
    print(json.dumps({"error": message}))
    return 2


def yaml_block(text):
    match = re.search(r"```yaml\n(.*?)```", text, re.S)
    return match.group(1) if match else text


def parse_checks(text):
    checks = []
    current = None
    for raw in yaml_block(text).splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith("- check:"):
            if current is not None:
                checks.append(current)
            current = {"check": line.split(":", 1)[1].strip()}
            continue
        if current is None:
            continue
        if line.startswith("  directory:"):
            current["directory"] = line.split(":", 1)[1].strip()
        elif line.startswith("  command:"):
            current["command"] = line.split(":", 1)[1].strip()
    if current is not None:
        checks.append(current)
    return checks


def run_check(entry):
    missing = REQUIRED - set(entry)
    if missing:
        return "fail", f"check {entry.get('check', '?')!r} is missing fields: {', '.join(sorted(missing))}"
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
    if not os.path.isfile(PRECOMMIT):
        print("null")
        return 0
    try:
        checks = parse_checks(open(PRECOMMIT).read())
    except Exception as exc:
        return die(f"could not parse {PRECOMMIT}: {exc}")
    if not checks:
        return die(f"{PRECOMMIT} contains no checks")
    results = []
    for entry in checks:
        status, detail = run_check(entry)
        results.append({"check": entry["check"], "status": status, "detail": detail})
    print(json.dumps(results, indent=2))
    return 0 if all(r["status"] == "pass" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
