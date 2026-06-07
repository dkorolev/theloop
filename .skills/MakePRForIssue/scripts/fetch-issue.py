#!/usr/bin/env python3
"""Fetch a GitHub issue from the repo in .theloop/repo.txt.

Usage (from the repository root):
  fetch-issue.py --issue-number N

Output: JSON with number, title, body, url, and labels on stdout.
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
    parser.add_argument("--issue-number", required=True)
    args = parser.parse_args()
    try:
        number = int(args.issue_number)
    except (TypeError, ValueError):
        die("--issue-number must be a positive integer")
    if number <= 0:
        die("--issue-number must be a positive integer")

    slug = read_repo_slug()
    proc = subprocess.run(
        [
            "gh", "issue", "view", str(number),
            "-R", slug,
            "--json", "number,title,body,url,labels",
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "gh issue view failed").strip()
        die(detail)

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        die(f"gh issue view returned invalid JSON: {exc}")

    labels = payload.get("labels") or []
    label_names = []
    for label in labels:
        if isinstance(label, dict) and "name" in label:
            label_names.append(label["name"])
        elif isinstance(label, str):
            label_names.append(label)

    result = {
        "number": payload.get("number"),
        "title": payload.get("title"),
        "body": payload.get("body") or "",
        "url": payload.get("url"),
        "labels": label_names,
    }
    if not isinstance(result["number"], int) or not result["title"] or not result["url"]:
        die("gh issue view did not return number, title, and url")

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
