#!/usr/bin/env python3
"""Check whether this repository has completed newrepo-theloopify-internal-postinit.

Usage: .skills/PreCommitSkillForClientRepos/scripts/check-configured.py   (from the repository root)

The gate keys off the positive marker .theloop/configure_the_loop.done, never the
mere absence of the pending marker, so deleting the pending marker cannot bypass it.

- .theloop/theloopified absent  -> this is not a theloopified client repo (for example
  the theloop development repo); the gate does not apply and reports configured.
- .theloop/configure_the_loop.done present -> configured.
- otherwise -> not configured: the user must run newrepo-theloopify-internal-postinit first.

Output: a JSON object {"configured", "applicable", "detail"} on stdout.
Exit code: 0 when configured (or not applicable), 1 when configuration is pending.
"""
import json
import os
import sys

THELOOPIFIED = os.path.join(".theloop", "theloopified")
DONE = os.path.join(".theloop", "configure_the_loop.done")


def main():
    if not os.path.exists(THELOOPIFIED):
        print(json.dumps({
            "configured": True,
            "applicable": False,
            "detail": "not a theloopified repository; the configuration gate does not apply",
        }, indent=2))
        return 0
    if os.path.exists(DONE):
        print(json.dumps({"configured": True, "applicable": True, "detail": None}, indent=2))
        return 0
    print(json.dumps({
        "configured": False,
        "applicable": True,
        "detail": "configuration is pending: run newrepo-theloopify-internal-postinit before any other workflow skill",
    }, indent=2))
    return 1


if __name__ == "__main__":
    sys.exit(main())
