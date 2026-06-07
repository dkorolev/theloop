#!/usr/bin/env python3
"""Mark ConfigureTheLoop complete: write the done marker, remove the pending marker.

Usage: .skills/ConfigureTheLoopForClientRepos/scripts/mark-configured.py [--summary TEXT]
       (from the repository root)

Writes .theloop/configure_the_loop.done (a short marker with the completion time and
an optional one-line summary) and removes .theloop/must_run_configure_the_loop.txt.
Refuses if .theloop/configure_the_loop.done already exists, so configuration is
flipped at most once.

Output: a JSON object {"done_path", "removed_must_run"} on stdout.
Exit code: 0 on success, 1 on error (one-line message on stderr).
"""
import argparse
import datetime
import json
import os
import sys
from typing import NoReturn

THELOOP_DIR = ".theloop"
MUST_RUN = os.path.join(THELOOP_DIR, "must_run_configure_the_loop.txt")
DONE = os.path.join(THELOOP_DIR, "configure_the_loop.done")


def die(message) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--summary", default="")
    args = parser.parse_args()

    if not os.path.isdir(THELOOP_DIR):
        die(f"{THELOOP_DIR}/ does not exist; this repository is not theloopified")
    if os.path.exists(DONE):
        die(f"{DONE} already exists; configuration is flipped at most once")

    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"configured: {stamp}"]
    if args.summary.strip():
        lines.append(args.summary.strip())
    with open(DONE, "x") as f:
        f.write("\n".join(lines) + "\n")

    removed = False
    if os.path.exists(MUST_RUN):
        os.remove(MUST_RUN)
        removed = True

    print(json.dumps({"done_path": DONE, "removed_must_run": removed}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
