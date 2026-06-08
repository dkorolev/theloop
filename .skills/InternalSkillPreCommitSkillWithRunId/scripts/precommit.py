#!/usr/bin/env python3
"""Single-shot primitive for the PRECOMMIT.md checks — it never schedules concurrency.

Scheduling is the skill prompt's job: InternalSkillPreCommitSkillWithRunId fans out one
subagent per check and runs them in parallel. This script only ever does one of two dumb,
deterministic things:

  precommit.py --list
      Parse the YAML check list in PRECOMMIT.md (inside a ```yaml fenced block, or the whole
      file when no fence is present) and print it as a JSON array of
      {"check", "directory", "command"} objects. Prints null when PRECOMMIT.md is absent.
      Exit 0; exit 2 when the file exists but cannot be parsed or lists no checks.

  precommit.py --checks-file PATH
      Run the JSON check list at PATH — typically the single check a fanned-out subagent owns —
      each command from its own directory, and print a JSON array of
      {"check", "status", "detail"} outcomes ("detail" is null unless the check fails).
      Exit 0 when every check passes, 1 when at least one fails, 2 when PATH is unreadable.

Run it from the repository root.
"""
import argparse
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


def do_list():
    if not os.path.isfile(PRECOMMIT):
        print("null")
        return 0
    try:
        checks = parse_checks(open(PRECOMMIT).read())
    except Exception as exc:
        return die(f"could not parse {PRECOMMIT}: {exc}")
    if not checks:
        return die(f"{PRECOMMIT} contains no checks")
    print(json.dumps(checks, indent=2))
    return 0


def do_run(path):
    if not os.path.isfile(path):
        return die(f"checks file not found: {path}")
    try:
        checks = json.load(open(path))
    except json.JSONDecodeError as exc:
        return die(f"could not parse {path}: {exc}")
    if not isinstance(checks, list):
        return die(f"{path} must contain a JSON array")
    results = []
    for entry in checks:
        status, detail = run_check(entry)
        results.append({"check": entry.get("check", "?"), "status": status, "detail": detail})
    print(json.dumps(results, indent=2))
    return 0 if all(r["status"] == "pass" for r in results) else 1


def main():
    parser = argparse.ArgumentParser(add_help=False)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true")
    mode.add_argument("--checks-file")
    args = parser.parse_args()
    return do_list() if args.list else do_run(args.checks_file)


if __name__ == "__main__":
    sys.exit(main())
