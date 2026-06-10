#!/usr/bin/env python3
"""Check the rule registry and enumerate rules, per .theloop/RULE-FILES.md."""
import json
import os
import subprocess
import sys

REGISTRY = "ai-rules.yml"
PROBE_SCRIPT = ".skills/InternalSkillCheckSingleRuleWithRunId/scripts/rules.py"


def non_ignored_files(pathspec=None):
    cmd = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
    if pathspec is not None:
        cmd += ["--", pathspec]
    try:
        listed = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=120).stdout.splitlines()
    except subprocess.TimeoutExpired:
        raise ValueError("timeout: git ls-files exceeded 120s")
    return sorted(p for p in set(listed) if os.path.isfile(p))


def registered_rules():
    if not os.path.isfile(REGISTRY):
        return None
    rules = []
    for line in open(REGISTRY):
        line = line.split("#", 1)[0].strip()
        if not line or line == "[]":
            continue
        if not line.startswith("- "):
            raise ValueError(f"{REGISTRY} is not a flat YAML list of paths: unexpected line {line!r}")
        rules.append(line[2:].strip())
    return rules


def sub_run_suffix(rule_path):
    return rule_path.replace("/", "-").removesuffix(".yml")


def probe_one(rule_path):
    try:
        result = subprocess.run([PROBE_SCRIPT, "probe-one", rule_path], capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        raise ValueError(f"timeout: probe-one {rule_path} exceeded 120s")
    if result.returncode == 2:
        raise ValueError(json.loads(result.stdout)["error"])
    return json.loads(result.stdout)


def main():
    if len(sys.argv) != 2 or sys.argv[1] != "probe":
        print(json.dumps({"error": "usage: rules.py probe"}))
        return 2
    actual = [p for p in non_ignored_files() if p.endswith("-rule.yml")]
    try:
        registered = registered_rules()
    except ValueError as exc:
        print(json.dumps({"registry": {"status": "fail", "detail": str(exc)}, "rules": []}, indent=2))
        return 1
    problems = []
    if registered is None:
        registered = []
        if actual:
            problems.append(f"{REGISTRY} does not exist, but the repo contains rules: " + ", ".join(actual))
    else:
        for stale in sorted(set(registered) - set(actual)):
            problems.append(f"{REGISTRY} lists {stale}, which is not a non-ignored *-rule.yml file of the repo")
        for missing in sorted(set(actual) - set(registered)):
            problems.append(f"{missing} is missing from {REGISTRY}")
    rules = []
    for rule_path in sorted(set(registered) & set(actual)):
        probed = probe_one(rule_path)
        entry = {
            "rule": rule_path,
            "directory": os.path.dirname(rule_path) or ".",
            "sub_run_suffix": sub_run_suffix(rule_path),
            "check": f"rule:{rule_path}",
            "parse_status": probed.get("parse_status", "pass"),
            "fingerprint": probed.get("fingerprint"),
            "cached": probed.get("cached", False),
            "cache_path": probed.get("cache_path"),
            "scope_files": probed.get("scope_files", []),
        }
        if probed.get("parse_status") == "fail":
            entry["detail"] = probed.get("detail")
        rules.append(entry)
    print(json.dumps({
        "registry": {"status": "fail" if problems else "pass", "detail": "; ".join(problems) if problems else None},
        "rules": rules,
    }, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
