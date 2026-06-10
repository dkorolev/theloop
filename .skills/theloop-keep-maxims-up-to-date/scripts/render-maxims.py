#!/usr/bin/env python3
"""Generate a maxim category's .md from its .yml source of truth, printing to stdout.

Usage (from the repository root):
  render-maxims.py maxims/FRONTEND.yml

The .yml is the single source of truth; this prints exactly the .md that should exist
for it. Use it to (re)generate a category's .md, and to iterate a hand-edited .md back
into agreement with its .yml.

Exit code: 0 on success, 1 on any error (one-line message on stderr).
"""
import os
import sys

from common import die, load_category, render_md


def main():
    if len(sys.argv) != 2:
        die("usage: render-maxims.py <path-to-category.yml>")
    path = sys.argv[1]
    if not os.path.isfile(path):
        die(f"{path} does not exist")
    sys.stdout.write(render_md(load_category(path)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
