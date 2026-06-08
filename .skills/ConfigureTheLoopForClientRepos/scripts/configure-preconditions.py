#!/usr/bin/env python3
"""Check whether theloop-post-setuprepo is allowed to run in this repository.

Usage: .skills/ConfigureTheLoopForClientRepos/scripts/configure-preconditions.py
       (from the repository root)

States, in priority order:
- .theloop/configure_the_loop.done present -> refuse: already configured (single-run).
- .theloop/theloopified absent             -> refuse: not a theloopified repo; run theloopify first.
- .theloop/must_run_configure_the_loop.txt absent -> refuse: configuration is not pending.
- otherwise                                -> allowed.

Output: a JSON object {"allowed", "reason", "detail"} on stdout.
Exit code: 0 when allowed, 1 when refused.
"""
import json
import os
import sys

THELOOPIFIED = os.path.join(".theloop", "theloopified")
MUST_RUN = os.path.join(".theloop", "must_run_configure_the_loop.txt")
DONE = os.path.join(".theloop", "configure_the_loop.done")


def refuse(reason, detail):
    print(json.dumps({"allowed": False, "reason": reason, "detail": detail}, indent=2))
    return 1


def main():
    if os.path.exists(DONE):
        return refuse("already-configured",
                      f"{DONE} exists; theloop-post-setuprepo runs at most once per clone")
    if not os.path.exists(THELOOPIFIED):
        return refuse("not-theloopified",
                      f"{THELOOPIFIED} is absent; run theloopify on this repository first")
    if not os.path.exists(MUST_RUN):
        return refuse("not-pending",
                      f"{MUST_RUN} is absent; configuration is not pending for this repository")
    print(json.dumps({"allowed": True, "reason": None, "detail": None}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
