#!/usr/bin/env python3
"""Create a GitHub pull request with the theloop label.

Usage (from the repository root):
  create-pr.py --title TITLE --body-file PATH --head BRANCH [--base BASE]

Output: JSON with pr_number and pr_url on stdout.
Exit code: 0 on success, 1 on any error (one-line message on stderr).
"""
import argparse
import json
import os
import re
import subprocess
import sys
from typing import NoReturn

REPO_FILE = os.path.join(".theloop", "repo.txt")
THELOOP_LABEL = "theloop"


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
    parser.add_argument("--title", required=True)
    parser.add_argument("--body-file", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--base", default="main")
    args = parser.parse_args()

    title = args.title.strip()
    head = args.head.strip()
    base = args.base.strip()
    if not title:
        die("--title must be non-empty")
    if not head:
        die("--head must be non-empty")

    if not os.path.isfile(args.body_file):
        die(f"body file not found: {args.body_file}")

    slug = read_repo_slug()
    proc = subprocess.run(
        [
            "gh", "pr", "create",
            "-R", slug,
            "--title", title,
            "--body-file", args.body_file,
            "--head", head,
            "--base", base,
            "--label", THELOOP_LABEL,
            "--json", "number,url",
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        die((proc.stderr or proc.stdout or "gh pr create failed").strip())

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        die(f"gh pr create returned invalid JSON: {exc}")

    number = payload.get("number")
    url = payload.get("url")
    if not isinstance(number, int) or not isinstance(url, str) or not url:
        die("gh pr create did not return pr number and url")

    print(json.dumps({"pr_number": number, "pr_url": url}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
