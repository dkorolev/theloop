#!/usr/bin/env python3
"""Validate and write the run receipt of PreCommitSkillWithRunId, write-once.

Usage: .skills/PreCommitSkillWithRunId/scripts/write-receipt.py < receipt.json   (from the repository root)
Reads one JSON object on stdin, checks it against the fixed receipt schema of
PreCommitSkillWithRunId, and writes it to tmp/<skill_run_id>.json, refusing to
overwrite an existing file.
Output: the path of the written receipt on stdout.
Exit code: 0 on success, 1 on any error (one-line message on stderr).
"""
import json
import os
import re
import sys
from typing import NoReturn

SKILL = "PreCommitSkillWithRunId"
FIELDS = {"skill_run_id", "skill", "status", "hygiene_checks", "invariants", "extra_checks", "validation", "cache_summary", "error"}
STATUSES = {"pass", "fail", "error"}
SOURCES = {"cache", "regenerated"}
SUMMARY_FIELDS = {"cached", "regenerated"}
INVARIANT_CHECK_FIELDS = {"invariant", "status", "source", "detail"}
VALIDATION_FIELDS = {"sub_run_id", "status", "source", "cache_summary"}


def die(message) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def summarize_sources(entries):
    cached = sum(1 for entry in entries if entry.get("source") == "cache")
    regenerated = sum(1 for entry in entries if entry.get("source") == "regenerated")
    return {"cached": cached, "regenerated": regenerated}


def merge_summaries(*summaries):
    merged = {"cached": 0, "regenerated": 0}
    for summary in summaries:
        merged["cached"] += summary["cached"]
        merged["regenerated"] += summary["regenerated"]
    return merged


def validation_source(summary):
    if summary["cached"] == 0 and summary["regenerated"] == 0:
        return None
    if summary["regenerated"] == 0:
        return "cache"
    return "regenerated"


def validate_cache_summary(summary):
    if not isinstance(summary, dict) or set(summary) != SUMMARY_FIELDS:
        die(f'"cache_summary" must be an object with exactly the fields {sorted(SUMMARY_FIELDS)}')
    for key in SUMMARY_FIELDS:
        if not isinstance(summary[key], int) or summary[key] < 0:
            die(f'"cache_summary.{key}" must be a non-negative integer')


def validate_validation(validation):
    if not isinstance(validation, dict) or set(validation) != VALIDATION_FIELDS:
        die(f'"validation" must be an object with exactly the fields {sorted(VALIDATION_FIELDS)}')
    if validation["status"] not in STATUSES:
        die('"validation.status" must be "pass", "fail", or "error"')
    validate_cache_summary(validation["cache_summary"])
    if validation["status"] == "error":
        if validation["source"] is not None:
            die('"validation.source" must be null when validation.status is "error"')
    elif validation["source"] not in SOURCES:
        die('"validation.source" must be "cache" or "regenerated" when validation.status is not "error"')


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
    if not isinstance(receipt["hygiene_checks"], list):
        die('"hygiene_checks" must be a list')
    if receipt["status"] == "error":
        if receipt["invariants"] is not None:
            die('"invariants" must be null when status is "error"')
    else:
        if not isinstance(receipt["invariants"], dict):
            die('"invariants" must be an object when status is "pass" or "fail"')
        if not isinstance(receipt["invariants"].get("registry"), dict):
            die('"invariants.registry" must be an object')
        if not isinstance(receipt["invariants"].get("checks"), list):
            die('"invariants.checks" must be a list')
        for check in receipt["invariants"]["checks"]:
            if not isinstance(check, dict) or set(check) != INVARIANT_CHECK_FIELDS:
                die(f'each entry of "invariants.checks" must have exactly the fields {sorted(INVARIANT_CHECK_FIELDS)}')
            if check["source"] not in SOURCES:
                die('each invariant check must have "source" set to "cache" or "regenerated"')
        validate_validation(receipt["validation"])
    if receipt["extra_checks"] is not None and not isinstance(receipt["extra_checks"], list):
        die('"extra_checks" must be a list or null')
    if (receipt["status"] == "error") != (receipt["error"] is not None):
        die('"error" must be set when and only when status is "error"')
    if receipt["status"] != "error":
        validate_cache_summary(receipt["cache_summary"])
        invariant_summary = summarize_sources(receipt["invariants"]["checks"])
        expected = merge_summaries(invariant_summary, receipt["validation"]["cache_summary"])
        if receipt["cache_summary"] != expected:
            die(f'"cache_summary" must merge invariants and validation: expected {expected}, got {receipt["cache_summary"]}')
        expected_validation_source = validation_source(receipt["validation"]["cache_summary"])
        if receipt["validation"]["source"] != expected_validation_source:
            die(f'"validation.source" must match validation.cache_summary: expected {expected_validation_source!r}, got {receipt["validation"]["source"]!r}')
    if receipt["status"] == "pass":
        failing = [c.get("check") for c in receipt["hygiene_checks"] + (receipt["extra_checks"] or [])
                   if c.get("status") != "pass"]
        inv_reg_ok = receipt["invariants"]["registry"].get("status") == "pass"
        inv_checks_ok = all(c.get("status") == "pass" for c in receipt["invariants"]["checks"])
        validation = receipt["validation"]
        if failing or not inv_reg_ok or not inv_checks_ok or not (isinstance(validation, dict) and validation.get("status") == "pass"):
            die('status "pass" requires every hygiene, invariant, and extra check to pass and the validation sub-run to report "pass"')

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
