#!/usr/bin/env python3
"""Validate and write the run receipt of CheckSingleInvariantWithRunId, write-once.

Usage (CLI — preferred):
  write-receipt.py --skill-run-id ID --invariant PATH --status pass --source cache|regenerated
  write-receipt.py --skill-run-id ID --invariant PATH --status fail --source regenerated --detail "REASON"
  write-receipt.py --skill-run-id ID --invariant PATH --status error --error "REASON"

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

SKILL = "CheckSingleInvariantWithRunId"
FIELDS = {"skill_run_id", "skill", "invariant", "status", "source", "detail", "error"}
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
    if not isinstance(receipt["invariant"], str) or not receipt["invariant"]:
        die('"invariant" must be a non-empty string')
    if receipt["status"] not in STATUSES:
        die('"status" must be "pass", "fail", or "error"')
    if receipt["status"] == "error":
        if receipt["source"] is not None:
            die('"source" must be null when status is "error"')
        if receipt["error"] is None:
            die('"error" must be set when status is "error"')
    else:
        if receipt["source"] not in SOURCES:
            die('"source" must be "cache" or "regenerated" when status is not "error"')
        if receipt["error"] is not None:
            die('"error" must be null when status is not "error"')
    if receipt["status"] != "fail" and receipt["detail"] is not None:
        die('"detail" must be null when status is not "fail"')
    if receipt["status"] == "fail" and not isinstance(receipt["detail"], str):
        die('"detail" must be a string when status is "fail"')


def build_from_args(args):
    if args.status == "error":
        if not args.error:
            die("--error is required when --status error")
        return {
            "skill_run_id": args.skill_run_id,
            "skill": SKILL,
            "invariant": args.invariant,
            "status": "error",
            "source": None,
            "detail": None,
            "error": args.error,
        }
    if not args.source:
        die("--source is required when --status is not 'error'")
    if args.status == "fail" and not args.detail:
        die("--detail is required when --status fail")
    return {
        "skill_run_id": args.skill_run_id,
        "skill": SKILL,
        "invariant": args.invariant,
        "status": args.status,
        "source": args.source,
        "detail": args.detail if args.status == "fail" else None,
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
        parser.add_argument("--invariant", required=True)
        parser.add_argument("--status", required=True, choices=list(STATUSES))
        parser.add_argument("--source")
        parser.add_argument("--detail")
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
