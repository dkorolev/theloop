#!/usr/bin/env python3
"""Validate and write the run receipt of theloop-internal-check-single-rule, write-once."""
import argparse
import json
import os
import re
import sys
from typing import NoReturn

SKILL = "theloop-internal-check-single-rule"
FIELDS = {"skill_run_id", "skill", "rule", "status", "source", "detail", "error"}
STATUSES = {"pass", "fail", "error"}
SOURCES = {"cache", "regenerated"}


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
    if not isinstance(receipt["rule"], str) or not receipt["rule"]:
        die('"rule" must be a non-empty string')
    if receipt["status"] not in STATUSES:
        die('"status" must be "pass", "fail", or "error"')
    if receipt["status"] == "error":
        if receipt["source"] is not None or receipt["error"] is None:
            die("invalid error receipt fields")
    else:
        if receipt["source"] not in SOURCES or receipt["error"] is not None:
            die("invalid non-error receipt fields")
    if receipt["status"] == "fail" and not isinstance(receipt["detail"], str):
        die('"detail" must be a string when status is "fail"')
    if receipt["status"] != "fail" and receipt["detail"] is not None:
        die('"detail" must be null when status is not "fail"')


def build_from_args(args):
    if args.status == "error":
        if not args.error:
            die("--error is required when --status error")
        return {"skill_run_id": args.skill_run_id, "skill": SKILL, "rule": args.rule,
                "status": "error", "source": None, "detail": None, "error": args.error}
    if not args.source:
        die("--source is required when --status is not 'error'")
    if args.status == "fail" and not args.detail:
        die("--detail is required when --status fail")
    return {"skill_run_id": args.skill_run_id, "skill": SKILL, "rule": args.rule,
            "status": args.status, "source": args.source,
            "detail": args.detail if args.status == "fail" else None, "error": None}


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
    parser.add_argument("--rule", required=True)
    parser.add_argument("--status", required=True, choices=list(STATUSES))
    parser.add_argument("--source")
    parser.add_argument("--detail")
    parser.add_argument("--error")
    args = parser.parse_args()
    receipt = build_from_args(args)
    validate(receipt)
    write_receipt(receipt)


if __name__ == "__main__":
    main()
