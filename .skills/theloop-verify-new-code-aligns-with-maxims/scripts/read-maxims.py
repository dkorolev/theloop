#!/usr/bin/env python3
"""List the maxims categories to verify against, validating the maxims/ artifact.

Usage: .skills/theloop-verify-new-code-aligns-with-maxims/scripts/read-maxims.py   (from the repository root)

This skill only reads maxims/; the artifact is owned and written by
theloop-keep-maxims-up-to-date.

- maxims/ absent -> error: there is nothing to verify against; run
  theloop-keep-maxims-up-to-date first.
- maxims/ present without metadata.json (the ownership marker) -> error: the path
  belongs to something else.
- otherwise prints the per-category .yml source-of-truth files listed in
  metadata.json, erroring when a listed file is missing.

Output: JSON {"categories": [{"id", "path"}, ...]} or {"error": "..."} on stdout.
Exit code: 0 on success, 1 on any error.
"""
import json
import os
import sys

MAXIMS_DIR = "maxims"
MARKER = os.path.join(MAXIMS_DIR, "metadata.json")


def fail(message):
    print(json.dumps({"error": message}))
    return 1


def main():
    if not os.path.isdir(MAXIMS_DIR):
        return fail("maxims/ does not exist: there are no maxims to verify against; run theloop-keep-maxims-up-to-date first")
    if not os.path.isfile(MARKER):
        return fail("maxims/ exists but has no metadata.json ownership marker: the path belongs to something else, not to the maxims artifact")
    try:
        with open(MARKER) as f:
            metadata = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        return fail(f"cannot read {MARKER}: {exc}")
    categories = metadata.get("categories")
    if not isinstance(categories, list) or not all(isinstance(c, str) for c in categories):
        return fail(f"{MARKER} has no valid 'categories' list")
    if not categories:
        return fail("metadata.json lists no categories: there are no maxims to verify against; run theloop-keep-maxims-up-to-date first")
    result = []
    for filename in sorted(categories):
        path = os.path.join(MAXIMS_DIR, filename)
        if not os.path.isfile(path):
            return fail(f"{MARKER} lists {filename}, but {path} does not exist")
        result.append({"id": filename.removesuffix(".yml"), "path": path})
    print(json.dumps({"categories": result}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
