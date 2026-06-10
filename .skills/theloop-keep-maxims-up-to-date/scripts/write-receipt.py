#!/usr/bin/env python3
"""Validate and write the run receipt of theloop-keep-maxims-up-to-date, write-once.

Usage (CLI — preferred):
  write-receipt.py --skill-run-id ID --status pass \
      --prs-considered N --maxims-written N \
      --categories-touched "frontend,backend" --human-decisions-requested N
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

SKILL = "theloop-keep-maxims-up-to-date"
FIELDS = {
    "skill_run_id", "skill", "status",
    "prs_considered", "maxims_written", "categories_touched",
    "human_decisions_requested", "error",
}
STATUSES = {"pass", "error"}
COUNTS = ("prs_considered", "maxims_written", "human_decisions_requested")


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
        die('"status" must be "pass" or "error"')

    is_error = receipt["status"] == "error"
    if is_error:
        for field in COUNTS + ("categories_touched",):
            if receipt[field] is not None:
                die(f'"{field}" must be null when status is "error"')
    else:
        for field in COUNTS:
            if not isinstance(receipt[field], int) or isinstance(receipt[field], bool) or receipt[field] < 0:
                die(f'"{field}" must be a non-negative integer when status is "pass"')
        if not isinstance(receipt["categories_touched"], list) or \
                not all(isinstance(c, str) for c in receipt["categories_touched"]):
            die('"categories_touched" must be a list of strings when status is "pass"')
    if is_error != (receipt["error"] is not None):
        die('"error" must be set when and only when status is "error"')


def build_from_args(args):
    if args.status == "error":
        if not args.error:
            die("--error is required when --status error")
        return {
            "skill_run_id": args.skill_run_id, "skill": SKILL, "status": "error",
            "prs_considered": None, "maxims_written": None, "categories_touched": None,
            "human_decisions_requested": None, "error": args.error,
        }
    counts = {}
    for flag, attr in (("--prs-considered", "prs_considered"),
                       ("--maxims-written", "maxims_written"),
                       ("--human-decisions-requested", "human_decisions_requested")):
        value = getattr(args, attr)
        if value is None:
            die(f"{flag} is required when --status is not 'error'")
        try:
            counts[attr] = int(value)
        except (TypeError, ValueError):
            die(f"{flag} must be a non-negative integer")
        if counts[attr] < 0:
            die(f"{flag} must be a non-negative integer")
    categories = [c.strip() for c in (args.categories_touched or "").split(",") if c.strip()]
    return {
        "skill_run_id": args.skill_run_id, "skill": SKILL, "status": "pass",
        "categories_touched": categories, "error": None, **counts,
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
        parser.add_argument("--prs-considered")
        parser.add_argument("--maxims-written")
        parser.add_argument("--categories-touched")
        parser.add_argument("--human-decisions-requested")
        parser.add_argument("--error")
        receipt = build_from_args(parser.parse_args())
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
