#!/usr/bin/env python3
"""Collect a batch of merged pull requests as judgment-ready evidence, on stdout.

Usage (from the repository root):
  fetch-prs.py --run-id SKILL_RUN_ID [--limit N] [--no-commit-files]

This is the slow, collect-half of the work. It lists merged-only PRs (most recent
first), skips any already considered, and for each gathers ordered commits, the
reworked-files signal, inline review comments, review summaries, and discussion
comments. Each fully-collected PR is cached atomically to the gitignored
maxims/cache/<pr>.json; a PR already cached is reused instead of re-fetched, so an
interrupted run resumes without repeating the slow fetch. The batch digest is printed
to stdout for in-context judgment; the cache is gitignored, never committed.

Exit code: 0 on success, 1 on any error (one-line message on stderr).
"""
import argparse
import json
import sys

from common import die, read_metadata, repo_slug, GhClient, GhError, read_pr_cache, write_pr_cache


def excerpt(text, limit=2000):
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit] + " …"


def digest_pr(gh, pr, include_commit_files):
    number = pr["number"]
    detail = gh.pr_view(number)
    commits = detail.get("commits", [])
    commit_rows = [{"oid": (c.get("oid") or "")[:7], "headline": c.get("messageHeadline")}
                   for c in commits]

    reworked = None
    if include_commit_files and len(commits) > 1:
        counts = {}
        for c in commits:
            for path in gh.commit_files(c.get("oid")):
                counts[path] = counts.get(path, 0) + 1
        reworked = sorted(p for p, n in counts.items() if n > 1)

    reviews = [{"author": (r.get("author") or {}).get("login"),
                "state": r.get("state"), "body": excerpt(r.get("body"))}
               for r in detail.get("reviews", []) if r.get("state") or r.get("body")]
    discussion = [{"author": (c.get("author") or {}).get("login"), "body": excerpt(c.get("body"))}
                  for c in detail.get("comments", [])]
    inline = gh.inline_review_comments(number)
    for c in inline:
        c["body"] = excerpt(c["body"])

    return {
        "number": number,
        "title": detail.get("title"),
        "url": detail.get("url"),
        "merged_at": detail.get("mergedAt"),
        "author": (detail.get("author") or {}).get("login"),
        "files_changed": sorted(f.get("path") for f in detail.get("files", []) if f.get("path")),
        "commits": commit_rows,
        "reworked_files": reworked,
        "reviews": reviews,
        "inline_comments": inline,
        "discussion_comments": discussion,
    }


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--no-commit-files", action="store_true")
    args = parser.parse_args()
    if args.limit < 1:
        die("--limit must be a positive integer")

    meta = read_metadata()
    considered = set(meta["analyzed_prs"])
    slug = repo_slug(required=True)
    gh = GhClient(slug)
    gh.ensure_access()

    try:
        listing = gh.list_merged_prs(args.limit + len(considered))
        fresh = [pr for pr in listing if pr["number"] not in considered][:args.limit]
        digests, reused = [], 0
        for pr in fresh:
            cached = read_pr_cache(pr["number"])
            if cached is not None:                       # already collected on an earlier run
                digests.append(cached)
                reused += 1
            else:                                        # slow collect, then cache atomically
                digest = digest_pr(gh, pr, not args.no_commit_files)
                write_pr_cache(pr["number"], digest, args.run_id)
                digests.append(digest)
    except GhError as exc:
        die(str(exc))

    print(json.dumps({
        "repo": slug,
        "considered_count": len(considered),
        "fetched_count": len(digests),
        "reused_from_cache": reused,
        "newly_collected": len(digests) - reused,
        "note": "each PR is collected once into the gitignored maxims/cache/<pr>.json and "
                "reused on later batches (no re-fetch). reworked_files is null for a "
                "single-commit PR (e.g. squash-merge) with no in-PR rework signal — lean on "
                "reviewer steering then. Keep looping until fetched_count is 0: every merged "
                "PR must be processed, not just this batch.",
        "prs": digests,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
