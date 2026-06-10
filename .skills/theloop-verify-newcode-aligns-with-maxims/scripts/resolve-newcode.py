#!/usr/bin/env python3
"""Resolve the new code to verify: the linear chain of commits on top of the origin's main.

Usage: .skills/theloop-verify-newcode-aligns-with-maxims/scripts/resolve-newcode.py --run-id ID
       (from the repository root)

Performs, with every git call time-bounded:
  1. fetch the origin's main branch (using origin/HEAD's target when known, else "main");
  2. require the current branch to sit squarely on top of it: the origin's main tip
     must be the merge base of the two, and origin/main..HEAD must contain no merge
     commits — otherwise exit with a clear message telling the user to rebase first;
  3. write the payload — every commit in the range, in order, with its full message,
     stat, and diff — to the gitignored tmp/<run-id>-newcode.txt.

This script is read-only with respect to the repository's content: it never stages,
commits, or modifies tracked files; its only writes are under the gitignored tmp/.

Output: JSON {"status": "ok", "base", "head", "branch", "main_ref", "commit_count",
"commits": [{"sha", "subject"}, ...], "payload_path"} on stdout, or {"error": "..."}.
Exit code: 0 on success (including zero new commits), 1 on any error.
"""
import argparse
import json
import os
import subprocess
import sys

TIMEOUT = 120


def git(*args):
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        print(json.dumps({"error": f"timeout: git {' '.join(args)} exceeded {TIMEOUT}s"}))
        sys.exit(1)


def fail(message):
    print(json.dumps({"error": message}))
    return 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    remotes = git("remote")
    if remotes.returncode != 0:
        return fail("not a git repository, or git is unavailable")
    if "origin" not in remotes.stdout.split():
        return fail("no 'origin' remote is configured; add one pointing at the GitHub repository first")

    head_ref = git("symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    main_branch = head_ref.stdout.strip().removeprefix("refs/remotes/origin/") if head_ref.returncode == 0 and head_ref.stdout.strip() else "main"

    fetch = git("fetch", "origin", main_branch)
    if fetch.returncode != 0:
        reason = fetch.stderr.strip().splitlines()[-1] if fetch.stderr.strip() else "unknown error"
        return fail(f"git fetch origin {main_branch} failed: {reason}")

    base_run = git("rev-parse", "--verify", f"refs/remotes/origin/{main_branch}")
    if base_run.returncode != 0:
        return fail(f"origin/{main_branch} does not exist after the fetch")
    base = base_run.stdout.strip()

    head_run = git("rev-parse", "--verify", "HEAD")
    if head_run.returncode != 0:
        return fail("cannot resolve HEAD: the repository has no commits")
    head = head_run.stdout.strip()
    branch_run = git("rev-parse", "--abbrev-ref", "HEAD")
    branch = branch_run.stdout.strip() if branch_run.returncode == 0 else "HEAD"

    merge_base = git("merge-base", base, head)
    if merge_base.returncode != 0 or merge_base.stdout.strip() != base:
        return fail(
            f"the current branch is not squarely on top of origin/{main_branch}: "
            f"rebase your branch onto the origin's {main_branch} first, then re-run this skill"
        )
    merges = git("rev-list", "--merges", f"{base}..{head}")
    if merges.stdout.strip():
        return fail(
            f"the range origin/{main_branch}..HEAD contains merge commits: "
            f"rebase your branch into a linear history on top of the origin's {main_branch} first, then re-run this skill"
        )

    log = git("log", "--reverse", "--format=%H%x09%s", f"{base}..{head}")
    commits = [
        {"sha": line.split("\t", 1)[0], "subject": line.split("\t", 1)[1]}
        for line in log.stdout.splitlines() if line.strip()
    ]

    payload_path = None
    if commits:
        payload = git("log", "--reverse", "--stat", "--patch", f"{base}..{head}")
        if payload.returncode != 0:
            return fail("git log --patch failed over the resolved range")
        payload_path = os.path.join("tmp", f"{args.run_id}-newcode.txt")
        os.makedirs("tmp", exist_ok=True)
        temp_path = f"{payload_path}.{args.run_id}.tmp"
        with open(temp_path, "w") as f:
            f.write(payload.stdout)
        os.replace(temp_path, payload_path)

    print(json.dumps({
        "status": "ok",
        "base": base,
        "head": head,
        "branch": branch,
        "main_ref": f"origin/{main_branch}",
        "commit_count": len(commits),
        "commits": commits,
        "payload_path": payload_path,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
