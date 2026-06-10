#!/usr/bin/env python3
"""Initialize maxims/ and inventory the conventions a repository already documents.

Usage (from the repository root):
  init-maxims.py --run-id SKILL_RUN_ID

Creates maxims/ (with metadata.json and a .gitignore) when absent; when it already
exists, re-scans and reconciles the convention inventory without ever touching
recorded maxims or the considered-PR set. Refuses to adopt a maxims/ it did not
create — one lacking metadata.json.

Output: a JSON summary on stdout, including the convention files the runner should
read so it knows what is already covered.
Exit code: 0 on success, 1 on any error (one-line message on stderr).
"""
import argparse
import glob
import os
import sys

from common import (
    die, MAXIMS_DIR, METADATA_PATH, GITIGNORE_PATH, GITIGNORE_BODY,
    maxims_state, new_metadata, read_metadata, dumps,
    create_new, update_metadata, write_text_atomic,
)

CONVENTION_PATTERNS = [
    "CONTRIBUTING*", ".github/CONTRIBUTING*",
    "CLAUDE.md", "AGENTS.md", "GEMINI.md", ".cursorrules",
    ".cursor/rules/**/*.md", ".cursor/rules/**/*.mdc",
    "STYLE*", "STYLEGUIDE*", "docs/STYLE*", "docs/style*",
    ".editorconfig",
    ".eslintrc*", "eslint.config.*",
    ".prettierrc*", "prettier.config.*",
    ".stylelintrc*",
    "ruff.toml", ".ruff.toml", ".flake8", "setup.cfg", "pyproject.toml",
    ".rubocop.yml", ".golangci.yml", ".golangci.yaml",
]
IGNORE_PREFIXES = tuple(p + os.sep for p in (MAXIMS_DIR, ".git", "node_modules", "tmp", "__pycache__"))


def scan():
    found = set()
    for pat in CONVENTION_PATTERNS:
        for path in glob.glob(pat, recursive=True):
            norm = os.path.normpath(path)
            if os.path.isfile(norm) and not norm.startswith(IGNORE_PREFIXES):
                found.add(norm)
    return sorted(found)


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    if maxims_state() == "foreign":
        die(f"{MAXIMS_DIR}/ exists but has no metadata.json; it belongs to something "
            f"else — refusing to initialize over it")

    os.makedirs(MAXIMS_DIR, exist_ok=True)
    # keep the .gitignore current — it ignores the cache/ dir and the *.tmp / *.lock temps
    if not os.path.exists(GITIGNORE_PATH) or \
            open(GITIGNORE_PATH, encoding="utf-8").read() != GITIGNORE_BODY:
        write_text_atomic(GITIGNORE_PATH, GITIGNORE_BODY, args.run_id)

    conventions = scan()

    def reconcile(m):
        m["existing_conventions"] = conventions

    created = False
    if not os.path.isfile(METADATA_PATH):
        meta = new_metadata()
        meta["existing_conventions"] = conventions
        try:
            create_new(METADATA_PATH, dumps(meta))
            created = True
        except FileExistsError:
            update_metadata(reconcile, args.run_id)
    else:
        update_metadata(reconcile, args.run_id)

    meta = read_metadata()
    print(dumps({
        "created": created,
        "existing_conventions": conventions,
        "categories": meta.get("categories", []),
        "considered_prs": len(meta.get("analyzed_prs", [])),
        "read_these": conventions,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
