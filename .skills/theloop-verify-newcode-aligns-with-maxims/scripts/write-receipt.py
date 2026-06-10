#!/usr/bin/env python3
"""Validate and write the run receipt of theloop-verify-newcode-aligns-with-maxims, write-once.

Usage (CLI):
  write-receipt.py --skill-run-id ID --status pass \
      --base SHA --head SHA --commits-checked N --categories-checked "a,b"
  write-receipt.py --skill-run-id ID --status fail \
      --base SHA --head SHA --commits-checked N --categories-checked "a,b" \
      --violations-json '[{"maxim": "...", "category": "...", "evidence": "...", "detail": "..."}]'
  write-receipt.py --skill-run-id ID --status error --error "REASON"

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

SKILL = "theloop-verify-newcode-aligns-with-maxims"
FIELDS = {
    "skill_run_id", "skill", "status",
    "base", "head", "commits_checked", "categories_checked", "violations",
    "error",
}
STATUSES = {"pass", "fail", "error"}
VIOLATION_FIELDS = {"maxim", "category", "evidence", "detail"}
SHA = re.compile(r"[0-9a-f]{7,64}\Z")


def die(message) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def validate(receipt):
    if set(receipt) != FIELDS:
        die(f"the receipt fields must be exactly {sorted(FIELDS)}, got {sorted(receipt)}")
    if not isinstance(receipt["skill_run_id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", receipt["skill_run_id"]):
        die('"skill_run_id" must be a non-empty string of letters, digits, and dashes')
    if receipt["skill"] != SKILL:
        die(f'"skill" must be "{SKILL}"')
    if receipt["status"] not in STATUSES:
        die('"status" must be "pass", "fail", or "error"')

    if receipt["status"] == "error":
        for field in ("base", "head", "commits_checked", "categories_checked", "violations"):
            if receipt[field] is not None:
                die(f'"{field}" must be null when status is "error"')
        if not isinstance(receipt["error"], str) or not receipt["error"].strip():
            die('"error" must be a non-empty string when status is "error"')
        return

    if receipt["error"] is not None:
        die('"error" must be null unless status is "error"')
    for field in ("base", "head"):
        if not isinstance(receipt[field], str) or not SHA.fullmatch(receipt[field]):
            die(f'"{field}" must be a git SHA string')
    if not isinstance(receipt["commits_checked"], int) or isinstance(receipt["commits_checked"], bool) or receipt["commits_checked"] < 0:
        die('"commits_checked" must be a non-negative integer')
    if not isinstance(receipt["categories_checked"], list) or not all(isinstance(c, str) and c for c in receipt["categories_checked"]):
        die('"categories_checked" must be a list of non-empty strings')
    violations = receipt["violations"]
    if not isinstance(violations, list):
        die('"violations" must be a list')
    for v in violations:
        if not isinstance(v, dict) or set(v) != VIOLATION_FIELDS:
            die(f"every violation must be an object with exactly the fields {sorted(VIOLATION_FIELDS)}")
        for field in VIOLATION_FIELDS:
            if not isinstance(v[field], str) or not v[field].strip():
                die(f'violation field "{field}" must be a non-empty string')
    if receipt["status"] == "pass" and violations:
        die('"violations" must be empty when status is "pass"')
    if receipt["status"] == "fail" and not violations:
        die('"violations" must be non-empty when status is "fail"')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-run-id", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--commits-checked", type=int)
    parser.add_argument("--categories-checked")
    parser.add_argument("--violations-json", default="[]")
    parser.add_argument("--error")
    args = parser.parse_args()

    if args.status == "error":
        receipt = {
            "skill_run_id": args.skill_run_id, "skill": SKILL, "status": "error",
            "base": None, "head": None, "commits_checked": None,
            "categories_checked": None, "violations": None,
            "error": args.error,
        }
    else:
        try:
            violations = json.loads(args.violations_json)
        except json.JSONDecodeError as exc:
            die(f"--violations-json is not valid JSON: {exc}")
        categories = [c for c in (args.categories_checked or "").split(",") if c]
        receipt = {
            "skill_run_id": args.skill_run_id, "skill": SKILL, "status": args.status,
            "base": args.base, "head": args.head, "commits_checked": args.commits_checked,
            "categories_checked": categories, "violations": violations,
            "error": None,
        }

    validate(receipt)
    path = os.path.join("tmp", f"{receipt['skill_run_id']}.json")
    if os.path.exists(path):
        die(f"{path} already exists and must never be overwritten")
    os.makedirs("tmp", exist_ok=True)
    with open(path, "w") as f:
        json.dump(receipt, f, indent=2)
        f.write("\n")
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
