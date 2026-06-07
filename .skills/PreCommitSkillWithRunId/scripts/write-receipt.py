#!/usr/bin/env python3
"""Validate and write the run receipt of PreCommitSkillWithRunId, write-once.

Usage (CLI — preferred):
  write-receipt.py --skill-run-id ID \
      --hygiene-json '[{"check":"tmp-gitignored","status":"pass","detail":null},...]' \
      --invariants-sub-run-id ID \
      --extra-checks-json '[...]'|null \
      --validation-sub-run-id ID

  write-receipt.py --skill-run-id ID --status error --error "REASON" [--hygiene-json '[...]']

  --invariants-sub-run-id  CheckAllInvariantsWithRunId sub-run identifier (its receipt is read from tmp/)
  --extra-checks-json      JSON array from precommit.py, or the string "null" when PRECOMMIT.md is absent
  --validation-sub-run-id  ValidateAllSkills sub-run identifier (its receipt is read from tmp/)

  The script reads the sub-run receipts, computes cache_summary, derives the overall status,
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


def read_sub_run_receipt(sub_run_id):
    path = os.path.join("tmp", sub_run_id + ".json")
    if not os.path.exists(path):
        die(f"sub-run receipt not found: {path}")
    with open(path) as f:
        return json.load(f)


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


def build_from_args(args):
    # Parse hygiene checks
    hygiene_checks = []
    if args.hygiene_json:
        try:
            hygiene_checks = json.loads(args.hygiene_json)
        except json.JSONDecodeError as exc:
            die(f"--hygiene-json is not valid JSON: {exc}")
        if not isinstance(hygiene_checks, list):
            die("--hygiene-json must be a JSON array")

    if args.status == "error":
        if not args.error:
            die("--error is required when --status error")
        return {
            "skill_run_id": args.skill_run_id,
            "skill": SKILL,
            "status": "error",
            "hygiene_checks": hygiene_checks,
            "invariants": None,
            "extra_checks": None,
            "validation": None,
            "cache_summary": {"cached": 0, "regenerated": 0},
            "error": args.error,
        }

    if not args.invariants_sub_run_id:
        die("--invariants-sub-run-id is required when status is not 'error'")
    if not args.validation_sub_run_id:
        die("--validation-sub-run-id is required when status is not 'error'")

    # Read invariants sub-run receipt
    inv_sub = read_sub_run_receipt(args.invariants_sub_run_id)
    registry = inv_sub.get("registry", {"status": "fail", "detail": "missing"})
    inv_checks = []
    for entry in (inv_sub.get("invariants") or []):
        inv_checks.append({
            "invariant": entry["invariant"],
            "status": entry["status"],
            "source": entry["source"],
            "detail": entry.get("detail"),
        })

    # Parse extra checks
    extra_checks = None
    if args.extra_checks_json and args.extra_checks_json.strip().lower() != "null":
        try:
            extra_checks = json.loads(args.extra_checks_json)
        except json.JSONDecodeError as exc:
            die(f"--extra-checks-json is not valid JSON: {exc}")
        if not isinstance(extra_checks, list):
            die("--extra-checks-json must be a JSON array or null")

    # Read validation sub-run receipt
    val_sub = read_sub_run_receipt(args.validation_sub_run_id)
    val_cache_summary = val_sub.get("cache_summary", {"cached": 0, "regenerated": 0})
    val_source = validation_source(val_cache_summary)
    validation = {
        "sub_run_id": args.validation_sub_run_id,
        "status": val_sub["status"],
        "source": val_source,
        "cache_summary": val_cache_summary,
    }

    # Compute overall cache_summary
    inv_summary = summarize_sources(inv_checks)
    cache_summary = merge_summaries(inv_summary, val_cache_summary)

    # Derive overall status
    hygiene_ok = all(c.get("status") == "pass" for c in hygiene_checks)
    inv_reg_ok = registry.get("status") == "pass"
    inv_checks_ok = all(c.get("status") == "pass" for c in inv_checks)
    extra_ok = extra_checks is None or all(c.get("status") == "pass" for c in extra_checks)
    val_ok = val_sub["status"] == "pass"
    status = "pass" if (hygiene_ok and inv_reg_ok and inv_checks_ok and extra_ok and val_ok) else "fail"

    return {
        "skill_run_id": args.skill_run_id,
        "skill": SKILL,
        "status": status,
        "hygiene_checks": hygiene_checks,
        "invariants": {"registry": registry, "checks": inv_checks},
        "extra_checks": extra_checks,
        "validation": validation,
        "cache_summary": cache_summary,
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
        parser.add_argument("--invariants-sub-run-id")
        parser.add_argument("--extra-checks-json")
        parser.add_argument("--validation-sub-run-id")
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
