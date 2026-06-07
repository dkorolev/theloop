#!/usr/bin/env python3
"""Validate and write the run receipt of InternalSkillPreCommitForClientWithRunId, write-once.

Usage (CLI — preferred):
  write-receipt.py --skill-run-id ID --hygiene-json '[...]' --extra-checks-json '[...]|null'
  write-receipt.py --skill-run-id ID --status error --error "REASON" [--hygiene-json '[...]']

  The script derives the overall status from the hygiene and extra checks,
  validates the schema, and refuses to overwrite an existing file.

Usage (stdin — fallback):
  write-receipt.py < receipt.json

Output: the path of the written receipt on stdout.
Exit code: 0 on success, 1 on any error (one-line message on stderr).
"""
import argparse
import json
import os
import re
import sys
from typing import NoReturn

SKILL = "InternalSkillPreCommitForClientWithRunId"
FIELDS = {"skill_run_id", "skill", "status", "hygiene_checks", "extra_checks", "error"}
STATUSES = {"pass", "fail", "error"}
CHECK_FIELDS = {"check", "status", "detail"}


def die(message) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def parse_json_list(raw, flag):
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        die(f"{flag} is not valid JSON: {exc}")
    if not isinstance(value, list):
        die(f"{flag} must be a JSON array")
    return value


def validate_checks(checks, where):
    for entry in checks:
        if not isinstance(entry, dict) or set(entry) != CHECK_FIELDS:
            die(f'each entry of "{where}" must have exactly the fields {sorted(CHECK_FIELDS)}')
        if entry["status"] not in {"pass", "fail"}:
            die(f'each entry of "{where}" must have status "pass" or "fail"')


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
    if not isinstance(receipt["hygiene_checks"], list):
        die('"hygiene_checks" must be a list')
    validate_checks(receipt["hygiene_checks"], "hygiene_checks")
    if receipt["extra_checks"] is not None:
        if not isinstance(receipt["extra_checks"], list):
            die('"extra_checks" must be a list or null')
        validate_checks(receipt["extra_checks"], "extra_checks")
    if (receipt["status"] == "error") != (receipt["error"] is not None):
        die('"error" must be set when and only when status is "error"')

    if receipt["status"] != "error":
        extra = receipt["extra_checks"] or []
        all_pass = (all(c["status"] == "pass" for c in receipt["hygiene_checks"])
                    and all(c["status"] == "pass" for c in extra))
        if receipt["status"] == "pass" and not all_pass:
            die('status "pass" requires every hygiene and extra check to pass')
        if receipt["status"] == "fail" and all_pass:
            die('status "fail" requires at least one failing hygiene or extra check')


def build_from_args(args):
    if args.status == "error":
        if not args.error:
            die("--error is required when --status error")
        hygiene = parse_json_list(args.hygiene_json, "--hygiene-json") if args.hygiene_json else []
        return {
            "skill_run_id": args.skill_run_id,
            "skill": SKILL,
            "status": "error",
            "hygiene_checks": hygiene,
            "extra_checks": None,
            "error": args.error,
        }

    if args.hygiene_json is None:
        die("--hygiene-json is required unless --status error")
    hygiene = parse_json_list(args.hygiene_json, "--hygiene-json")
    if args.extra_checks_json is None or args.extra_checks_json.strip() == "null":
        extra = None
    else:
        extra = parse_json_list(args.extra_checks_json, "--extra-checks-json")

    checks = list(hygiene) + list(extra or [])
    status = "pass" if all(c.get("status") == "pass" for c in checks) else "fail"

    return {
        "skill_run_id": args.skill_run_id,
        "skill": SKILL,
        "status": status,
        "hygiene_checks": hygiene,
        "extra_checks": extra,
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
        parser.add_argument("--status", default=None)
        parser.add_argument("--hygiene-json")
        parser.add_argument("--extra-checks-json")
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
