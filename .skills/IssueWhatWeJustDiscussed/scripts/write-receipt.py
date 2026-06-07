#!/usr/bin/env python3
"""Validate and write the run receipt of IssueWhatWeJustDiscussed, write-once.

Usage (CLI — preferred):
  write-receipt.py --skill-run-id ID --status pass \
      --feature-title TITLE --feature-summary TEXT \
      --issue-number N --issue-url URL --gh-check-sub-run-id ID
  write-receipt.py --skill-run-id ID --status fail \
      --gh-check-sub-run-id ID [--issue-number N] [--issue-url URL]
  write-receipt.py --skill-run-id ID --status error --error "REASON"

Validates the receipt against the fixed schema and writes it to tmp/<skill_run_id>.json,
refusing to overwrite an existing file.
Output: the path of the written receipt on stdout.
Exit code: 0 on success, 1 on any error (one-line message on stderr).
"""
import argparse
import json
import os
import re
import sys
from typing import NoReturn

SKILL = "IssueWhatWeJustDiscussed"
FIELDS = {
    "skill_run_id",
    "skill",
    "status",
    "feature_title",
    "feature_summary",
    "issue_number",
    "issue_url",
    "gh_check_sub_run_id",
    "error",
}
STATUSES = {"pass", "fail", "error"}
NULLABLE_ON_ERROR = {
    "feature_title",
    "feature_summary",
    "issue_number",
    "issue_url",
    "gh_check_sub_run_id",
}


def die(message) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


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

    is_error = receipt["status"] == "error"
    is_pass = receipt["status"] == "pass"

    for field in NULLABLE_ON_ERROR:
        if is_error and receipt[field] is not None:
            die(f'"{field}" must be null when status is "error"')

    if is_error:
        if receipt["error"] is None:
            die('"error" must be set when status is "error"')
        return

    if receipt["error"] is not None:
        die('"error" must be null when status is not "error"')

    if is_pass:
        for field in ("feature_title", "feature_summary", "issue_url", "gh_check_sub_run_id"):
            if not isinstance(receipt[field], str) or not receipt[field]:
                die(f'"{field}" must be a non-empty string when status is "pass"')
        if not isinstance(receipt["issue_number"], int) or receipt["issue_number"] <= 0:
            die('"issue_number" must be a positive integer when status is "pass"')
    else:
        if receipt["feature_title"] is not None and not isinstance(receipt["feature_title"], str):
            die('"feature_title" must be a string or null when status is "fail"')
        if receipt["feature_summary"] is not None and not isinstance(receipt["feature_summary"], str):
            die('"feature_summary" must be a string or null when status is "fail"')
        if receipt["issue_number"] is not None:
            if not isinstance(receipt["issue_number"], int) or receipt["issue_number"] <= 0:
                die('"issue_number" must be a positive integer or null when status is "fail"')
        if receipt["issue_url"] is not None and not isinstance(receipt["issue_url"], str):
            die('"issue_url" must be a string or null when status is "fail"')
        if receipt["gh_check_sub_run_id"] is not None:
            if not isinstance(receipt["gh_check_sub_run_id"], str) or not receipt["gh_check_sub_run_id"]:
                die('"gh_check_sub_run_id" must be a non-empty string or null when status is "fail"')


def build_from_args(args):
    if args.status == "error":
        if not args.error:
            die("--error is required when --status error")
        return {
            "skill_run_id": args.skill_run_id,
            "skill": SKILL,
            "status": "error",
            "feature_title": None,
            "feature_summary": None,
            "issue_number": None,
            "issue_url": None,
            "gh_check_sub_run_id": None,
            "error": args.error,
        }

    issue_number = None
    if args.issue_number is not None:
        try:
            issue_number = int(args.issue_number)
        except (TypeError, ValueError):
            die("--issue-number must be a positive integer")
        if issue_number <= 0:
            die("--issue-number must be a positive integer")

    receipt = {
        "skill_run_id": args.skill_run_id,
        "skill": SKILL,
        "status": args.status,
        "feature_title": args.feature_title,
        "feature_summary": args.feature_summary,
        "issue_number": issue_number,
        "issue_url": args.issue_url,
        "gh_check_sub_run_id": args.gh_check_sub_run_id,
        "error": None,
    }

    if args.status == "pass":
        for flag, key in (
            ("--feature-title", "feature_title"),
            ("--feature-summary", "feature_summary"),
            ("--issue-number", "issue_number"),
            ("--issue-url", "issue_url"),
            ("--gh-check-sub-run-id", "gh_check_sub_run_id"),
        ):
            if receipt[key] is None or receipt[key] == "":
                die(f"{flag} is required when --status is 'pass'")

    return receipt


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
    parser.add_argument("--status", required=True, choices=list(STATUSES))
    parser.add_argument("--feature-title")
    parser.add_argument("--feature-summary")
    parser.add_argument("--issue-number")
    parser.add_argument("--issue-url")
    parser.add_argument("--gh-check-sub-run-id")
    parser.add_argument("--error")
    args = parser.parse_args()
    receipt = build_from_args(args)
    validate(receipt)
    write_receipt(receipt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
