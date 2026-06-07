#!/usr/bin/env python3
"""Post a MakePRForIssue work claim on a GitHub issue and detect duplicate claims.

Usage (from the repository root):
  claim-issue-work.py --issue-number N

Posts a comment that the issue was taken into work by MakePRForIssue, then scans
other issue comments for the same claim. When another comment already claims the
issue, edits the new comment to strike out the claim and append a retraction.

Output: JSON with comment_id, comment_url, claimed, retracted, and
other_claim_comment_ids on stdout.
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
CLAIM_BODY = "Taken into work by **MakePRForIssue**."
RETRACTION_LINE = "Nevermind; already in the works."


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


def gh_api_json(args):
    proc = subprocess.run(["gh", "api", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        die((proc.stderr or proc.stdout or "gh api failed").strip())
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        die(f"gh api returned invalid JSON: {exc}")


def is_retracted(body):
    lower = body.lower()
    return "nevermind" in lower and "already in the works" in lower


def is_work_claim(body):
    if is_retracted(body):
        return False
    return "taken into work" in body.lower()


def retracted_body(original):
    return f"~~{original}~~\n\n{RETRACTION_LINE}"


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
    created = gh_api_json([
        f"repos/{slug}/issues/{number}/comments",
        "-f", f"body={CLAIM_BODY}",
    ])
    comment_id = created.get("id")
    comment_url = created.get("html_url")
    if not isinstance(comment_id, int) or not isinstance(comment_url, str) or not comment_url:
        die("GitHub did not return comment id and url after posting the claim")

    comments = gh_api_json([f"repos/{slug}/issues/{number}/comments"])
    if not isinstance(comments, list):
        die("GitHub did not return a list of issue comments")

    other_claim_ids = [
        entry["id"]
        for entry in comments
        if isinstance(entry, dict)
        and isinstance(entry.get("id"), int)
        and entry["id"] != comment_id
        and isinstance(entry.get("body"), str)
        and is_work_claim(entry["body"])
    ]

    retracted = False
    if other_claim_ids:
        gh_api_json([
            "-X", "PATCH",
            f"repos/{slug}/issues/comments/{comment_id}",
            "-f", f"body={retracted_body(CLAIM_BODY)}",
        ])
        retracted = True

    print(json.dumps({
        "comment_id": comment_id,
        "comment_url": comment_url,
        "claimed": not retracted,
        "retracted": retracted,
        "other_claim_comment_ids": other_claim_ids,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
