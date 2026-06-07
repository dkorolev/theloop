#!/usr/bin/env python3
"""Validate and write the run receipt of CheckAllInvariantsWithRunId, write-once.

Usage (CLI — preferred):
  write-receipt.py --skill-run-id ID --registry-status pass|fail [--registry-detail TEXT] \
      --sub-run-ids "id1 id2 ..."
  write-receipt.py --skill-run-id ID --status error --error "REASON"

  --sub-run-ids is a space-separated list of CheckSingleInvariantWithRunId sub-run identifiers.
  The script reads each sub-run receipt from tmp/, derives the overall status and cache_summary,
  and refuses to overwrite an existing file.

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

SKILL = "CheckAllInvariantsWithRunId"
FIELDS = {"skill_run_id", "skill", "status", "registry", "invariants", "cache_summary", "error"}
STATUSES = {"pass", "fail", "error"}
SOURCES = {"cache", "regenerated"}
REGISTRY_FIELDS = {"status", "detail"}
INVARIANT_FIELDS = {"invariant", "sub_run_id", "status", "source", "detail"}
SUMMARY_FIELDS = {"cached", "regenerated"}


def die(message) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def read_sub_run_receipt(sub_run_id):
    path = os.path.join("tmp", sub_run_id + ".json")
    if not os.path.exists(path):
        die(f"sub-run receipt not found: {path}")
    with open(path) as f:
        return json.load(f)


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

    if receipt["status"] == "error":
        if receipt["registry"] is not None:
            die('"registry" must be null when status is "error"')
        if receipt["invariants"] is not None:
            die('"invariants" must be null when status is "error"')
        if receipt["cache_summary"] is not None:
            die('"cache_summary" must be null when status is "error"')
        if receipt["error"] is None:
            die('"error" must be set when status is "error"')
    else:
        if receipt["error"] is not None:
            die('"error" must be null when status is not "error"')
        if not isinstance(receipt["registry"], dict) or set(receipt["registry"]) != REGISTRY_FIELDS:
            die(f'"registry" must be an object with exactly the fields {sorted(REGISTRY_FIELDS)}')
        if receipt["registry"]["status"] not in ("pass", "fail"):
            die('"registry.status" must be "pass" or "fail"')
        if not isinstance(receipt["invariants"], list):
            die('"invariants" must be a list')
        for entry in receipt["invariants"]:
            if not isinstance(entry, dict) or set(entry) != INVARIANT_FIELDS:
                die(f'each entry of "invariants" must have exactly the fields {sorted(INVARIANT_FIELDS)}')
            if entry["status"] not in STATUSES:
                die('each invariant entry must have "status" of "pass", "fail", or "error"')
            if entry["status"] == "error":
                if entry["source"] is not None:
                    die('invariant "source" must be null when status is "error"')
            elif entry["source"] not in SOURCES:
                die('invariant "source" must be "cache" or "regenerated" when status is not "error"')
        if not isinstance(receipt["cache_summary"], dict) or set(receipt["cache_summary"]) != SUMMARY_FIELDS:
            die(f'"cache_summary" must be an object with exactly the fields {sorted(SUMMARY_FIELDS)}')
        for key in SUMMARY_FIELDS:
            if not isinstance(receipt["cache_summary"][key], int) or receipt["cache_summary"][key] < 0:
                die(f'"cache_summary.{key}" must be a non-negative integer')
        expected_cached = sum(1 for e in receipt["invariants"] if e.get("source") == "cache")
        expected_regen = sum(1 for e in receipt["invariants"] if e.get("source") == "regenerated")
        if receipt["cache_summary"]["cached"] != expected_cached or receipt["cache_summary"]["regenerated"] != expected_regen:
            die(f'"cache_summary" must match invariant source counts: expected {{"cached": {expected_cached}, "regenerated": {expected_regen}}}')
        if receipt["status"] == "pass":
            if receipt["registry"]["status"] != "pass":
                die('status "pass" requires registry.status to be "pass"')
            if any(e.get("status") != "pass" for e in receipt["invariants"]):
                die('status "pass" requires every invariant entry to have status "pass"')


def build_from_args(args):
    if args.status == "error":
        if not args.error:
            die("--error is required when --status error")
        return {
            "skill_run_id": args.skill_run_id,
            "skill": SKILL,
            "status": "error",
            "registry": None,
            "invariants": None,
            "cache_summary": None,
            "error": args.error,
        }

    if not args.registry_status:
        die("--registry-status is required when status is not 'error'")
    registry = {
        "status": args.registry_status,
        "detail": args.registry_detail,
    }

    invariants = []
    if args.sub_run_ids:
        for sub_run_id in args.sub_run_ids.split():
            sub = read_sub_run_receipt(sub_run_id)
            invariants.append({
                "invariant": sub["invariant"],
                "sub_run_id": sub_run_id,
                "status": sub["status"],
                "source": sub.get("source"),
                "detail": sub.get("detail"),
            })

    cached = sum(1 for e in invariants if e.get("source") == "cache")
    regenerated = sum(1 for e in invariants if e.get("source") == "regenerated")

    all_pass = registry["status"] == "pass" and all(e["status"] == "pass" for e in invariants)
    status = "pass" if all_pass else "fail"

    return {
        "skill_run_id": args.skill_run_id,
        "skill": SKILL,
        "status": status,
        "registry": registry,
        "invariants": invariants,
        "cache_summary": {"cached": cached, "regenerated": regenerated},
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
        parser.add_argument("--registry-status")
        parser.add_argument("--registry-detail")
        parser.add_argument("--sub-run-ids")
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
