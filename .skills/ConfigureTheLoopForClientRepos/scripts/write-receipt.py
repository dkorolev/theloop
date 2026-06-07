#!/usr/bin/env python3
"""Validate and write the run receipt of ConfigureTheLoopForClientRepos, write-once.

Usage (CLI — preferred):
  write-receipt.py --skill-run-id ID --status pass --precommit-md-path PATH \
      --checks-configured "tests lint ..."
  write-receipt.py --skill-run-id ID --status fail [--precommit-md-path PATH]
  write-receipt.py --skill-run-id ID --status error --error "REASON"

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

SKILL = "ConfigureTheLoopForClientRepos"
FIELDS = {"skill_run_id", "skill", "status", "precommit_md_path", "checks_configured", "error"}
STATUSES = {"pass", "fail", "error"}


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
    if (receipt["status"] == "error") != (receipt["error"] is not None):
        die('"error" must be set when and only when status is "error"')

    if receipt["status"] == "pass":
        if not isinstance(receipt["precommit_md_path"], str) or not receipt["precommit_md_path"]:
            die('status "pass" requires a non-empty "precommit_md_path"')
        if not isinstance(receipt["checks_configured"], list):
            die('status "pass" requires "checks_configured" to be a list')
    elif receipt["status"] == "fail":
        if receipt["precommit_md_path"] is not None and not isinstance(receipt["precommit_md_path"], str):
            die('"precommit_md_path" must be a string or null')
        if receipt["checks_configured"] is not None:
            die('status "fail" requires "checks_configured" to be null')
    else:  # error
        if receipt["precommit_md_path"] is not None or receipt["checks_configured"] is not None:
            die('status "error" requires "precommit_md_path" and "checks_configured" to be null')


def build_from_args(args):
    status = args.status
    if status not in STATUSES:
        die('--status must be "pass", "fail", or "error"')
    if status == "error":
        if not args.error:
            die("--error is required when --status error")
        return {
            "skill_run_id": args.skill_run_id,
            "skill": SKILL,
            "status": "error",
            "precommit_md_path": None,
            "checks_configured": None,
            "error": args.error,
        }
    if status == "pass":
        if not args.precommit_md_path:
            die("--precommit-md-path is required when --status pass")
        checks = args.checks_configured.split() if args.checks_configured else []
        return {
            "skill_run_id": args.skill_run_id,
            "skill": SKILL,
            "status": "pass",
            "precommit_md_path": args.precommit_md_path,
            "checks_configured": checks,
            "error": None,
        }
    # fail
    return {
        "skill_run_id": args.skill_run_id,
        "skill": SKILL,
        "status": "fail",
        "precommit_md_path": args.precommit_md_path or None,
        "checks_configured": None,
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
        parser.add_argument("--status", required=True)
        parser.add_argument("--precommit-md-path")
        parser.add_argument("--checks-configured")
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
