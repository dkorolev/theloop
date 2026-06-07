#!/usr/bin/env python3
"""Check whether a git branch name is free locally and on the remote.

Usage (from the repository root):
  check-branch.py --branch NAME

Output: JSON with branch, available, local_exists, remote_exists on stdout.
Exit code: 0 when the branch is available, 1 when taken or on error.
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
    slug = parse_repo_slug(repo_url)
    if not slug:
        die(f"{REPO_FILE} does not contain a recognizable GitHub repository URL")
    return slug


def local_exists(branch):
    proc = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
    )
    return proc.returncode == 0


def remote_exists(branch, slug):
    url = f"https://github.com/{slug}.git"
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    proc = subprocess.run(
        ["git", "ls-remote", "--heads", url, f"refs/heads/{branch}"],
        capture_output=True,
        text=True,
        env=env,
    )
    if proc.returncode != 0:
        die((proc.stderr or proc.stdout or "git ls-remote failed").strip())
    return bool(proc.stdout.strip())


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--branch", required=True)
    args = parser.parse_args()
    branch = args.branch.strip()
    if not branch or "/" in branch or ".." in branch:
        die("--branch must be a non-empty branch name without slashes")

    slug = read_repo_slug()
    loc = local_exists(branch)
    rem = remote_exists(branch, slug)
    available = not loc and not rem
    print(json.dumps({
        "branch": branch,
        "available": available,
        "local_exists": loc,
        "remote_exists": rem,
    }, indent=2))
    return 0 if available else 1


if __name__ == "__main__":
    sys.exit(main())
