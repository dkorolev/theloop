#!/usr/bin/env python3
"""Verify Internal skill naming across every skill in the repository.

Usage: .skills/theloop-internal-precommit/scripts/internal-skill-names.py
       (from the repository root)
Output: one JSON object {"violations": [...]} on stdout; each violation has
{"skill", "detail"}.
Exit code: 0 when every skill complies, 1 when at least one violates the rule.
"""
import json
import os
import re
import sys

INTERNAL_PREFIX = "theloop-internal-"
SKILLS_DIR = ".skills"


def takes_skill_run_id(body):
    return re.search(r"^\s*1\.\s+`SkillRunId`", body, re.M) is not None


def main():
    violations = []
    for skill in sorted(
        d for d in os.listdir(SKILLS_DIR)
        if os.path.isfile(os.path.join(SKILLS_DIR, d, "SKILL.md"))
    ):
        path = os.path.join(SKILLS_DIR, skill, "SKILL.md")
        body = re.sub(r"\A---\n.*?\n---\n", "", open(path).read(), flags=re.S)
        if takes_skill_run_id(body):
            if not skill.startswith(INTERNAL_PREFIX):
                violations.append({
                    "skill": skill,
                    "detail": f"`{skill}` takes SkillRunId but does not begin with {INTERNAL_PREFIX}",
                })
        elif skill.startswith(INTERNAL_PREFIX):
            violations.append({
                "skill": skill,
                "detail": f"`{skill}` does not take SkillRunId but begins with {INTERNAL_PREFIX}",
            })
    print(json.dumps({"violations": violations}, indent=2))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
