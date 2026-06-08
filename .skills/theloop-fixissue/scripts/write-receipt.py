#!/usr/bin/env python3
"""Validate and write the run receipt of theloop-fixissue, write-once.

Usage (CLI — preferred):
  write-receipt.py --skill-run-id ID --status pass \
      --issue-number N --issue-url URL --branch NAME \
      --pr-number N --pr-url URL --feature-doc-path PATH \
      --implementation-attempts N --pre-commit-skill-run-id ID \
      --gh-check-sub-run-id ID --commits "sha1 sha2"
  write-receipt.py --skill-run-id ID --status fail \
      [--issue-number N] [--branch NAME] [--gh-check-sub-run-id ID] ...
  write-receipt.py --skill-run-id ID --status error --error "REASON"

Output: the path of the written receipt on stdout.
Exit code: 0 on success, 1 on any error (one-line message on stderr).
"""
import argparse
import json
import os
import re
import sys
from typing import NoReturn

SKILL = "theloop-fixissue"
FIELDS = {
    "skill_run_id",
    "skill",
    "status",
    "issue_number",
    "issue_url",
    "branch_name",
    "pr_number",
    "pr_url",
    "feature_doc_path",
    "implementation_attempts",
    "pre_commit_skill_run_id",
    "gh_check_sub_run_id",
    "commits",
    "error",
}
STATUSES = {"pass", "fail", "error"}
NULLABLE_ON_ERROR = {
    "issue_number",
    "issue_url",
    "branch_name",
    "pr_number",
    "pr_url",
    "feature_doc_path",
    "implementation_attempts",
    "pre_commit_skill_run_id",
    "gh_check_sub_run_id",
    "commits",
}


def die(message) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def parse_commits(raw):
    if raw is None:
        return None
    if raw == "":
        return []
    return [part for part in raw.split() if part]


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

    if not isinstance(receipt["commits"], list) and receipt["commits"] is not None:
        die('"commits" must be a list of strings or null')

    if is_error:
        if receipt["error"] is None:
            die('"error" must be set when status is "error"')
        return

    if receipt["error"] is not None:
        die('"error" must be null when status is not "error"')

    if receipt["commits"] is not None:
        for sha in receipt["commits"]:
            if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-fA-F]{7,40}", sha):
                die('each entry in "commits" must be a git SHA string')

    if is_pass:
        for field in (
            "issue_number", "issue_url", "branch_name", "pr_number", "pr_url",
            "feature_doc_path", "pre_commit_skill_run_id", "gh_check_sub_run_id",
        ):
            if field.endswith("_number"):
                if not isinstance(receipt[field], int) or receipt[field] <= 0:
                    die(f'"{field}" must be a positive integer when status is "pass"')
            elif receipt[field] is None or receipt[field] == "":
                die(f'"{field}" must be set when status is "pass"')
        if not isinstance(receipt["implementation_attempts"], int) or receipt["implementation_attempts"] < 1:
            die('"implementation_attempts" must be a positive integer when status is "pass"')
        if receipt["commits"] is None:
            die('"commits" must be a list (possibly empty) when status is "pass"')


def build_from_args(args):
    if args.status == "error":
        if not args.error:
            die("--error is required when --status error")
        return {
            "skill_run_id": args.skill_run_id,
            "skill": SKILL,
            "status": "error",
            "issue_number": None,
            "issue_url": None,
            "branch_name": None,
            "pr_number": None,
            "pr_url": None,
            "feature_doc_path": None,
            "implementation_attempts": None,
            "pre_commit_skill_run_id": None,
            "gh_check_sub_run_id": None,
            "commits": None,
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

    pr_number = None
    if args.pr_number is not None:
        try:
            pr_number = int(args.pr_number)
        except (TypeError, ValueError):
            die("--pr-number must be a positive integer")
        if pr_number <= 0:
            die("--pr-number must be a positive integer")

    attempts = None
    if args.implementation_attempts is not None:
        try:
            attempts = int(args.implementation_attempts)
        except (TypeError, ValueError):
            die("--implementation-attempts must be a non-negative integer")
        if attempts < 0:
            die("--implementation-attempts must be a non-negative integer")

    return {
        "skill_run_id": args.skill_run_id,
        "skill": SKILL,
        "status": args.status,
        "issue_number": issue_number,
        "issue_url": args.issue_url,
        "branch_name": args.branch_name,
        "pr_number": pr_number,
        "pr_url": args.pr_url,
        "feature_doc_path": args.feature_doc_path,
        "implementation_attempts": attempts,
        "pre_commit_skill_run_id": args.pre_commit_skill_run_id,
        "gh_check_sub_run_id": args.gh_check_sub_run_id,
        "commits": parse_commits(args.commits),
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
    parser.add_argument("--status", required=True, choices=list(STATUSES))
    parser.add_argument("--issue-number")
    parser.add_argument("--issue-url")
    parser.add_argument("--branch-name")
    parser.add_argument("--pr-number")
    parser.add_argument("--pr-url")
    parser.add_argument("--feature-doc-path")
    parser.add_argument("--implementation-attempts")
    parser.add_argument("--pre-commit-skill-run-id")
    parser.add_argument("--gh-check-sub-run-id")
    parser.add_argument("--commits")
    parser.add_argument("--error")
    args = parser.parse_args()
    receipt = build_from_args(args)
    validate(receipt)
    write_receipt(receipt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
