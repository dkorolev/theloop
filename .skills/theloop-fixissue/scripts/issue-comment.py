#!/usr/bin/env python3
"""Post a journal comment on a GitHub issue.

Usage (from the repository root):
  issue-comment.py --issue-number N --body TEXT
  issue-comment.py --issue-number N --body-file PATH

The comment body is prefixed with "**theloop journal** — " automatically.
Exit code: 0 on success, 1 on any error (one-line message on stderr).
"""
import argparse
import os
import re
import subprocess
import sys
from typing import NoReturn

REPO_FILE = os.path.join(".theloop", "repo.txt")
PREFIX = "**theloop journal** — "


def die(message) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def parse_repo_slug(url):
    url = url.strip()
    if not url:
        return None
    if re.fullmatch(r"[^/\s]+/[^/\s]+", url):
        return url.rstrip("/").removesuffix(".git")
    match = re.search(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", url)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    return None


def read_repo_slug():
    if not os.path.isfile(REPO_FILE):
        die(f"{REPO_FILE} is missing; the target repository is not configured")
    with open(REPO_FILE) as f:
        repo_url = f.read().strip()
    slug = parse_repo_slug(repo_url)
    if not slug:
        die(f"{REPO_FILE} does not contain a recognizable GitHub repository URL")
    return slug


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--issue-number", required=True)
    parser.add_argument("--body")
    parser.add_argument("--body-file")
    args = parser.parse_args()
    try:
        number = int(args.issue_number)
    except (TypeError, ValueError):
        die("--issue-number must be a positive integer")
    if number <= 0:
        die("--issue-number must be a positive integer")

    if args.body_file:
        if not os.path.isfile(args.body_file):
            die(f"body file not found: {args.body_file}")
        with open(args.body_file) as f:
            body = f.read().strip()
    elif args.body:
        body = args.body.strip()
    else:
        die("either --body or --body-file is required")

    if not body:
        die("comment body must be non-empty")

    slug = read_repo_slug()
    full_body = PREFIX + body
    proc = subprocess.run(
        ["gh", "issue", "comment", str(number), "-R", slug, "--body", full_body],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        die((proc.stderr or proc.stdout or "gh issue comment failed").strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
