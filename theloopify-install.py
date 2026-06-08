#!/usr/bin/env python3
"""Copy the theloop client skill bundle into a target repository.

Usage: theloopify-install.py THELOOP_ROOT TARGET   (invoked by theloopify.sh)

For every bundled skill it copies THELOOP_ROOT/.skills/<dev-name>/ into
TARGET/.theloop/skills/<client-name>/, rewriting file contents so that:
  - every ".skills/" path reference becomes ".theloop/skills/", and
  - every "*ForClientRepos" development name becomes its client-facing name.
Executable bits are preserved. It then creates, for each supported coding agent,
a symlink <agent>/skills/<client-name> -> ../../.theloop/skills/<client-name>.

This script does not touch anything outside TARGET (and only reads THELOOP_ROOT).

Output: a JSON object {"installed", "symlinks"} on stdout.
Exit code: 0 on success, 1 on error (one-line message on stderr).
"""
import json
import os
import shutil
import sys
from typing import NoReturn

# (development name in THELOOP_ROOT/.skills, client-facing name in the target)
BUNDLE = [
    ("theloop-makeissue", "theloop-makeissue"),
    ("theloop-fixissue", "theloop-fixissue"),
    ("theloop-buildthis", "theloop-buildthis"),
    ("InternalSkillCheckGhRepoAccessWithRunId", "InternalSkillCheckGhRepoAccessWithRunId"),
    ("PreCommitSkillForClientRepos", "theloop-precommit"),
    ("ConfigureTheLoopForClientRepos", "theloop-post-setuprepo"),
    ("InternalSkillPreCommitForClientWithRunId", "InternalSkillPreCommitForClientWithRunId"),
]

# Longest names first so a name is never a prefix of another during replacement.
NAME_REWRITES = [
    ("ConfigureTheLoopForClientRepos", "theloop-post-setuprepo"),
    ("PreCommitSkillForClientRepos", "theloop-precommit"),
    ("PreCommitSkill", "theloop-precommit"),
]

AGENT_DIRS = [".cursor", ".claude", ".codex", ".agents"]


def die(message) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def rewrite(text):
    for old, new in NAME_REWRITES:
        text = text.replace(old, new)
    return text.replace(".skills/", ".theloop/skills/")


def copy_skill(src_dir, dst_dir):
    for root, _, files in os.walk(src_dir):
        rel_root = os.path.relpath(root, src_dir)
        out_root = dst_dir if rel_root == "." else os.path.join(dst_dir, rel_root)
        os.makedirs(out_root, exist_ok=True)
        for name in files:
            src = os.path.join(root, name)
            dst = os.path.join(out_root, name)
            with open(src, "rb") as f:
                raw = f.read()
            try:
                out = rewrite(raw.decode("utf-8")).encode("utf-8")
            except UnicodeDecodeError:
                out = raw  # binary file: copy verbatim, no rewrite
            with open(dst, "wb") as f:
                f.write(out)
            shutil.copymode(src, dst)


def make_symlink(link_path, target):
    if os.path.lexists(link_path):
        os.remove(link_path)
    os.symlink(target, link_path)


def main():
    if len(sys.argv) != 3:
        die("usage: theloopify-install.py THELOOP_ROOT TARGET")
    theloop_root, target = sys.argv[1], sys.argv[2]
    skills_root = os.path.join(theloop_root, ".skills")

    installed = []
    for dev_name, client_name in BUNDLE:
        src_dir = os.path.join(skills_root, dev_name)
        if not os.path.isfile(os.path.join(src_dir, "SKILL.md")):
            die(f"bundled skill not found: {src_dir}/SKILL.md")
        dst_dir = os.path.join(target, ".theloop", "skills", client_name)
        if os.path.exists(dst_dir):
            die(f"refusing to overwrite existing {dst_dir}")
        copy_skill(src_dir, dst_dir)
        installed.append(client_name)

    symlinks = []
    for agent in AGENT_DIRS:
        skills_dir = os.path.join(target, agent, "skills")
        os.makedirs(skills_dir, exist_ok=True)
        for client_name in installed:
            link_path = os.path.join(skills_dir, client_name)
            make_symlink(link_path, os.path.join("..", "..", ".theloop", "skills", client_name))
            symlinks.append(os.path.join(agent, "skills", client_name))

    print(json.dumps({"installed": installed, "symlinks": symlinks}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
