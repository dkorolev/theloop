#!/usr/bin/env python3
"""Validate and write the run receipt of CheckAllInvariantsWithRunId, write-once.

Usage: .skills/CheckAllInvariantsWithRunId/scripts/write-receipt.py < receipt.json   (from the repository root)
Reads one JSON object on stdin, checks it against the fixed receipt schema of
CheckAllInvariantsWithRunId, and writes it to tmp/<skill_run_id>.json, refusing to
overwrite an existing file.
Output: the path of the written receipt on stdout.
Exit code: 0 on success, 1 on any error (one-line message on stderr).
"""
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


def main():
    try:
        receipt = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        die(f"stdin is not valid JSON: {exc}")
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

    path = os.path.join("tmp", receipt["skill_run_id"] + ".json")
    if os.path.exists(path):
        die(f"{path} already exists; run receipts are write-once")
    os.makedirs("tmp", exist_ok=True)
    with open(path, "x") as f:
        json.dump(receipt, f, indent=2)
        f.write("\n")
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
