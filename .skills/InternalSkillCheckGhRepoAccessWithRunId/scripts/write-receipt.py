#!/usr/bin/env python3
"""Validate and write the run receipt of InternalSkillCheckGhRepoAccessWithRunId, write-once."""
import argparse
import json
import os
import re
import sys
from typing import NoReturn

SKILL = "InternalSkillCheckGhRepoAccessWithRunId"
FIELDS = {"skill_run_id", "skill", "status", "repo_url", "checks", "error"}
STATUSES = {"pass", "fail", "error"}
CHECK_STATUSES = {"pass", "fail", "skipped"}
CHECK_NAMES = {
    "repo-config",
    "gh-installed",
    "gh-authenticated",
    "gh-repo-access",
    "gh-repo-pull",
}


def die(message) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def validate_check(entry):
    if not isinstance(entry, dict):
        die("each check must be an object")
    expected = {"check", "status", "detail", "suggestion"}
    if set(entry) != expected:
        die(f"each check must have exactly the fields {sorted(expected)}")
    if entry["check"] not in CHECK_NAMES:
        die(f'unknown check name: {entry["check"]!r}')
    if entry["status"] not in CHECK_STATUSES:
        die('each check "status" must be "pass", "fail", or "skipped"')
    if entry["status"] == "fail":
        if not isinstance(entry["detail"], str) or not entry["detail"]:
            die('"detail" must be a non-empty string when a check fails')
        if entry["suggestion"] is not None and not isinstance(entry["suggestion"], str):
            die('"suggestion" must be a string or null')
    else:
        if entry["detail"] is not None:
            die('"detail" must be null unless the check fails')
        if entry["suggestion"] is not None:
            die('"suggestion" must be null unless the check fails')


def validate(receipt):
    if not isinstance(receipt, dict):
        die("the receipt must be a JSON object")
    if set(receipt) != FIELDS:
        die(f"the receipt fields must be exactly {sorted(FIELDS)}, got {sorted(receipt)}")
    if not isinstance(receipt["skill_run_id"], str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9-]*", receipt["skill_run_id"]
    ):
        die('"skill_run_id" must be a non-empty string of letters, digits, and dashes')
    if receipt["skill"] != SKILL:
        die(f'"skill" must be "{SKILL}"')
    if receipt["status"] not in STATUSES:
        die('"status" must be "pass", "fail", or "error"')
    if receipt["repo_url"] is not None and not isinstance(receipt["repo_url"], str):
        die('"repo_url" must be a string or null')
    if not isinstance(receipt["checks"], list):
        die('"checks" must be a list')
    for entry in receipt["checks"]:
        validate_check(entry)
    if receipt["status"] == "error":
        if receipt["error"] is None:
            die('"error" must be set when status is "error"')
    else:
        if receipt["error"] is not None:
            die('"error" must be null when status is not "error"')
    if receipt["status"] == "pass":
        if any(c["status"] == "fail" for c in receipt["checks"]):
            die('status "pass" requires every check to pass or be skipped')


def derive_status(checks):
    if any(c["status"] == "fail" for c in checks):
        return "fail"
    return "pass"


def build_from_args(args):
    if args.status == "error":
        if not args.error:
            die("--error is required when --status error")
        return {
            "skill_run_id": args.skill_run_id,
            "skill": SKILL,
            "status": "error",
            "repo_url": None,
            "checks": [],
            "error": args.error,
        }

    if not args.checks_json:
        die("--checks-json is required when status is not 'error'")
    try:
        payload = json.loads(args.checks_json)
    except json.JSONDecodeError as exc:
        die(f"--checks-json is not valid JSON: {exc}")
    if not isinstance(payload, dict) or "checks" not in payload:
        die('--checks-json must be a JSON object with a "checks" array')
    checks = payload["checks"]
    if not isinstance(checks, list):
        die('"checks" must be a JSON array')

    return {
        "skill_run_id": args.skill_run_id,
        "skill": SKILL,
        "status": derive_status(checks),
        "repo_url": payload.get("repo_url"),
        "checks": checks,
        "error": None,
    }


def write_receipt(receipt):
    path = os.path.join("tmp", receipt["skill_run_id"] + ".json")
    if os.path.exists(path):
        die(f"{path} already exists; run receipts are write-once")
    os.makedirs("tmp", exist_ok=True)
    with open(path, "x") as f:
        json.dump(receipt, f, indent=2)
        f.write("\n")
    print(path)


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--skill-run-id", required=True)
    parser.add_argument("--status")
    parser.add_argument("--checks-json")
    parser.add_argument("--error")
    args = parser.parse_args()
    if args.status == "error":
        receipt = build_from_args(args)
    else:
        receipt = build_from_args(args)
    validate(receipt)
    write_receipt(receipt)


if __name__ == "__main__":
    main()
