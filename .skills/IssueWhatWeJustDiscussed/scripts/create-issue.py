#!/usr/bin/env python3
"""Create a GitHub issue with the theloop label on the repo in .theloop/repo.txt.

Usage (from the repository root):
  create-issue.py --title TITLE --body-file PATH

Output: JSON object with issue_number and issue_url on stdout.
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
    if not repo_url:
        die(f"{REPO_FILE} is empty; the target repository is not configured")
    slug = parse_repo_slug(repo_url)
    if not slug:
        die(f"{REPO_FILE} does not contain a recognizable GitHub repository URL")
    return slug


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--title", required=True)
    parser.add_argument("--body-file", required=True)
    args = parser.parse_args()

    title = args.title.strip()
    if not title:
        die("--title must be non-empty")

    body_path = args.body_file
    if not os.path.isfile(body_path):
        die(f"body file not found: {body_path}")

    slug = read_repo_slug()

    proc = subprocess.run(
        [
            "gh", "issue", "create",
            "-R", slug,
            "--title", title,
            "--body-file", body_path,
            "--label", THELOOP_LABEL,
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "gh issue create failed").strip()
        die(detail)

    output = (proc.stdout or proc.stderr or "").strip()
    match = re.search(r"github\.com/[^/\s]+/[^/\s]+/issues/(\d+)", output)
    if not match:
        die(f"gh issue create did not return an issue URL: {output or '(empty output)'}")
    number = int(match.group(1))
    url = output if output.startswith("http") else f"https://{output.lstrip('/')}"

    print(json.dumps({"issue_number": number, "issue_url": url}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
