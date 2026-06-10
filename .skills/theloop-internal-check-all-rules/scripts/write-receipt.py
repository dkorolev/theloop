#!/usr/bin/env python3
"""Validate and write the run receipt of theloop-internal-check-all-rules, write-once."""
import argparse
import json
import os
import re
import sys
from typing import NoReturn

SKILL = "theloop-internal-check-all-rules"
FIELDS = {"skill_run_id", "skill", "status", "registry", "rules", "cache_summary", "error"}
STATUSES = {"pass", "fail", "error"}
SOURCES = {"cache", "regenerated"}
REGISTRY_FIELDS = {"status", "detail"}
RULE_FIELDS = {"rule", "sub_run_id", "status", "source", "detail"}
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
    if not isinstance(receipt, dict) or set(receipt) != FIELDS:
        die(f"the receipt fields must be exactly {sorted(FIELDS)}")
    if receipt["skill"] != SKILL:
        die(f'"skill" must be "{SKILL}"')
    if receipt["status"] not in STATUSES:
        die('invalid status')
    if receipt["status"] == "error":
        if receipt["registry"] is not None or receipt["rules"] is not None or receipt["error"] is None:
            die("invalid error receipt")
    else:
        if not isinstance(receipt["registry"], dict) or set(receipt["registry"]) != REGISTRY_FIELDS:
            die("invalid registry")
        if not isinstance(receipt["rules"], list):
            die("rules must be a list")
        for entry in receipt["rules"]:
            if set(entry) != RULE_FIELDS:
                die("invalid rule entry")
        if receipt["status"] == "pass":
            if receipt["registry"]["status"] != "pass" or any(e["status"] != "pass" for e in receipt["rules"]):
                die('status pass requires all rules pass')


def build_from_args(args):
    if args.status == "error":
        return {"skill_run_id": args.skill_run_id, "skill": SKILL, "status": "error",
                "registry": None, "rules": None, "cache_summary": None, "error": args.error}
    registry = {"status": args.registry_status, "detail": args.registry_detail}
    rules = []
    if args.sub_run_ids:
        for sub_run_id in args.sub_run_ids.split():
            sub = read_sub_run_receipt(sub_run_id)
            rules.append({"rule": sub["rule"], "sub_run_id": sub_run_id, "status": sub["status"],
                          "source": sub.get("source"), "detail": sub.get("detail")})
    cached = sum(1 for e in rules if e.get("source") == "cache")
    regenerated = sum(1 for e in rules if e.get("source") == "regenerated")
    all_pass = registry["status"] == "pass" and all(e["status"] == "pass" for e in rules)
    return {"skill_run_id": args.skill_run_id, "skill": SKILL,
            "status": "pass" if all_pass else "fail", "registry": registry, "rules": rules,
            "cache_summary": {"cached": cached, "regenerated": regenerated}, "error": None}


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
    parser.add_argument("--status", default=None)
    parser.add_argument("--registry-status")
    parser.add_argument("--registry-detail")
    parser.add_argument("--sub-run-ids")
    parser.add_argument("--error")
    args = parser.parse_args()
    receipt = build_from_args(args)
    validate(receipt)
    write_receipt(receipt)


if __name__ == "__main__":
    main()
