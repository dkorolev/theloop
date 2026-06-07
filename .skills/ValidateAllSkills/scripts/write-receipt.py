#!/usr/bin/env python3
"""Validate and write the run receipt of ValidateAllSkills, write-once.

Usage: .skills/ValidateAllSkills/scripts/write-receipt.py < receipt.json   (from the repository root)
Reads one JSON object on stdin, checks it against the fixed receipt schema of
ValidateAllSkills, and writes it to tmp/<skill_run_id>.json, refusing to
overwrite an existing file.
Output: the path of the written receipt on stdout.
Exit code: 0 on success, 1 on any error (one-line message on stderr).
"""
import json
import os
import re
import sys
from typing import NoReturn

SKILL = "ValidateAllSkills"
FIELDS = {"skill_run_id", "skill", "status", "skills_checked", "repo_violations", "cache_summary", "error"}
STATUSES = {"pass", "fail", "error"}
SOURCES = {"cache", "regenerated"}
ENTRY_FIELDS = {"skill", "sub_run_id", "status", "source", "violations"}
SUMMARY_FIELDS = {"cached", "regenerated"}


def die(message) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def summarize_sources(entries):
    cached = sum(1 for entry in entries if entry.get("source") == "cache")
    regenerated = sum(1 for entry in entries if entry.get("source") == "regenerated")
    return {"cached": cached, "regenerated": regenerated}


def validate_cache_summary(summary):
    if not isinstance(summary, dict) or set(summary) != SUMMARY_FIELDS:
        die(f'"cache_summary" must be an object with exactly the fields {sorted(SUMMARY_FIELDS)}')
    for key in SUMMARY_FIELDS:
        if not isinstance(summary[key], int) or summary[key] < 0:
            die(f'"cache_summary.{key}" must be a non-negative integer')


def main():
    try:
        receipt = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        die(f"stdin is not valid JSON: {exc}")
    if not isinstance(receipt, dict):
        die("the receipt must be a JSON object")
    if set(receipt) != FIELDS:
        die(f"the receipt fields must be exactly {sorted(FIELDS)}, got {sorted(receipt)}")
    if not isinstance(receipt["skill_run_id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", receipt["skill_run_id"]):
        die('"skill_run_id" must be a non-empty string of letters, digits, and dashes')
    if receipt["skill"] != SKILL:
        die(f'"skill" must be "{SKILL}"')
    if receipt["status"] not in STATUSES:
        die('"status" must be "pass", "fail", or "error"')
    if not isinstance(receipt["skills_checked"], list) or not isinstance(receipt["repo_violations"], list):
        die('"skills_checked" and "repo_violations" must be lists')
    if (receipt["status"] == "error") != (receipt["error"] is not None):
        die('"error" must be set when and only when status is "error"')
    for entry in receipt["skills_checked"]:
        if not isinstance(entry, dict) or set(entry) != ENTRY_FIELDS:
            die(f'each entry of "skills_checked" must have exactly the fields {sorted(ENTRY_FIELDS)}')
        if entry["status"] == "error":
            if entry["source"] is not None:
                die('each entry of "skills_checked" must have "source" null when status is "error"')
        elif entry["source"] not in SOURCES:
            die('each entry of "skills_checked" must have "source" set to "cache" or "regenerated" when status is not "error"')
    validate_cache_summary(receipt["cache_summary"])
    expected = summarize_sources(receipt["skills_checked"])
    if receipt["cache_summary"] != expected:
        die(f'"cache_summary" must match skills_checked: expected {expected}, got {receipt["cache_summary"]}')
    failing = [s.get("skill") for s in receipt["skills_checked"]
               if not (isinstance(s, dict) and s.get("status") == "pass")]
    if receipt["status"] == "pass" and (failing or receipt["repo_violations"]):
        die('status "pass" requires every checked skill to pass and "repo_violations" to be empty')
    if receipt["status"] == "fail" and not failing and not receipt["repo_violations"]:
        die('status "fail" requires a failing skill or a repo violation')

    path = os.path.join("tmp", receipt["skill_run_id"] + ".json")
    if os.path.exists(path):
        die(f"{path} already exists; run receipts are write-once")
    os.makedirs("tmp", exist_ok=True)
    with open(path, "x") as f:
        json.dump(receipt, f, indent=2)
        f.write("\n")
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
