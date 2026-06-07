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
FIELDS = {"skill_run_id", "skill", "status", "hygiene_checks", "extra_checks", "validation", "error"}
STATUSES = {"pass", "fail", "error"}


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
    if not isinstance(receipt["hygiene_checks"], list):
        die('"hygiene_checks" must be a list')
    if receipt["extra_checks"] is not None and not isinstance(receipt["extra_checks"], list):
        die('"extra_checks" must be a list or null')
    if (receipt["status"] == "error") != (receipt["error"] is not None):
        die('"error" must be set when and only when status is "error"')
    if receipt["status"] == "pass":
        failing = [c.get("check") for c in receipt["hygiene_checks"] + (receipt["extra_checks"] or [])
                   if c.get("status") != "pass"]
        validation = receipt["validation"]
        if failing or not (isinstance(validation, dict) and validation.get("status") == "pass"):
            die('status "pass" requires every check to pass and the validation sub-run to report "pass"')

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
