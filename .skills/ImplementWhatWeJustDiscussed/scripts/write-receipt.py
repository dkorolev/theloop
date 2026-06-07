#!/usr/bin/env python3
"""Validate and write the run receipt of ImplementWhatWeJustDiscussed, write-once.

Usage (CLI — preferred):
  write-receipt.py --skill-run-id ID --status pass|fail \
      --feature-summary "TEXT" --feature-doc-path PATH \
      --implementation-attempts N --pre-commit-skill-run-id ID
  write-receipt.py --skill-run-id ID --status error --error "REASON"

Usage (stdin — fallback):
  write-receipt.py < receipt.json

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

SKILL = "ImplementWhatWeJustDiscussed"
FIELDS = {
    "skill_run_id", "skill", "status",
    "feature_summary", "feature_doc_path",
    "implementation_attempts", "pre_commit_skill_run_id",
    "error",
}
STATUSES = {"pass", "fail", "error"}
NULLABLE_WHEN_ERROR = {"feature_summary", "feature_doc_path", "implementation_attempts", "pre_commit_skill_run_id"}


def die(message) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def validate(receipt):
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

    is_error = receipt["status"] == "error"
    for field in NULLABLE_WHEN_ERROR:
        if is_error and receipt[field] is not None:
            die(f'"{field}" must be null when status is "error"')
        if not is_error and field == "implementation_attempts":
            if not isinstance(receipt[field], int) or receipt[field] < 0:
                die('"implementation_attempts" must be a non-negative integer when status is not "error"')
        if not is_error and field in ("feature_summary", "feature_doc_path", "pre_commit_skill_run_id"):
            if not isinstance(receipt[field], str):
                die(f'"{field}" must be a string when status is not "error"')
    if is_error != (receipt["error"] is not None):
        die('"error" must be set when and only when status is "error"')


def build_from_args(args):
    if args.status == "error":
        if not args.error:
            die("--error is required when --status error")
        return {
            "skill_run_id": args.skill_run_id,
            "skill": SKILL,
            "status": "error",
            "feature_summary": None,
            "feature_doc_path": None,
            "implementation_attempts": None,
            "pre_commit_skill_run_id": None,
            "error": args.error,
        }
    for flag in ("--feature-summary", "--feature-doc-path", "--implementation-attempts", "--pre-commit-skill-run-id"):
        attr = flag.lstrip("-").replace("-", "_")
        if getattr(args, attr, None) is None:
            die(f"{flag} is required when --status is not 'error'")
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
        "feature_summary": args.feature_summary,
        "feature_doc_path": args.feature_doc_path,
        "implementation_attempts": attempts,
        "pre_commit_skill_run_id": args.pre_commit_skill_run_id,
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
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--skill-run-id", required=True)
        parser.add_argument("--status", required=True, choices=list(STATUSES))
        parser.add_argument("--feature-summary")
        parser.add_argument("--feature-doc-path")
        parser.add_argument("--implementation-attempts")
        parser.add_argument("--pre-commit-skill-run-id")
        parser.add_argument("--error")
        args = parser.parse_args()
        receipt = build_from_args(args)
    else:
        try:
            receipt = json.load(sys.stdin)
        except json.JSONDecodeError as exc:
            die(f"stdin is not valid JSON: {exc}")

    validate(receipt)
    write_receipt(receipt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
