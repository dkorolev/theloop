#!/usr/bin/env python3
"""Atomically add merged PR numbers to the considered set.

Usage (from the repository root):
  consider-pr.py --run-id SKILL_RUN_ID --pr 123,130

Call this for every PR after reasoning about it — even one that yielded no maxim —
so it is never fetched or judged again. The considered set is a sorted array of PR
numbers in maxims/metadata.json; each insert is an idempotent, lost-update-safe
compare-and-swap, so a PR already present is a no-op.

Output: a JSON summary on stdout.
Exit code: 0 on success, 1 on any error (one-line message on stderr).
"""
import argparse
import bisect
import sys

from common import die, require_ready, read_metadata, update_metadata, dumps


def parse_prs(value):
    prs = []
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        if not token.isdigit() or int(token) <= 0:
            die(f"--pr takes comma-separated positive integers; got '{token}'")
        prs.append(int(token))
    if not prs:
        die("--pr listed no PR numbers")
    return prs


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--pr", required=True)
    args = parser.parse_args()
    require_ready()
    prs = parse_prs(args.pr)

    added, already = [], []

    def mutate(meta):
        arr = meta.setdefault("analyzed_prs", [])
        del added[:]
        del already[:]
        for pr in prs:
            i = bisect.bisect_left(arr, pr)
            if i < len(arr) and arr[i] == pr:
                already.append(pr)
            else:
                arr.insert(i, pr)
                added.append(pr)

    update_metadata(mutate, args.run_id)

    print(dumps({
        "considered": sorted(added),
        "already_considered": sorted(already),
        "total_considered": len(read_metadata()["analyzed_prs"]),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
