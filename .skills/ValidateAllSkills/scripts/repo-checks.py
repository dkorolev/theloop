#!/usr/bin/env python3
"""Whole-repo checks of ValidateAllSkills.

Usage: .skills/ValidateAllSkills/scripts/repo-checks.py   (from the repository root)
Enumerates the skills (the directories .skills/<SkillName>/ that contain a
SKILL.md file), reads the invocation relationships from the `invokes` field in
each skill's SKILL.md frontmatter, and checks that SKILLS.md, the two tables
of .ai/VIZ.md, and the Mermaid diagram of .ai/VIZ.md all list exactly those
skills and relationships.
Output: one JSON object {"skills", "invocations", "violations"} on stdout;
each violation is {"rule", "detail"} with the rule named as titled in .ai/RULES.md.
Exit code: 0 with no violations, 1 with violations, 2 when no skills are found.
"""
import json
import os
import re
import sys

RULE_SKILLS_MD = "The `SKILLS.md` file should be up to date"
RULE_VIZ = "Visualization and topology"


def main():
    skills = sorted(
        d for d in os.listdir(".skills")
        if os.path.isfile(os.path.join(".skills", d, "SKILL.md"))
    )
    if not skills:
        print("error: no skills found under .skills/", file=sys.stderr)
        return 2
    skill_set = set(skills)

    edges = set()
    for skill in skills:
        text = open(os.path.join(".skills", skill, "SKILL.md")).read()
        fm = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if fm:
            inv = re.search(r"^invokes:\s*\[([^\]]*)\]", fm.group(1), re.M)
            if inv:
                for invoked in [s.strip() for s in inv.group(1).split(",") if s.strip()]:
                    if invoked in skill_set and invoked != skill:
                        edges.add((skill, invoked))

    violations = []

    def compare(rule, where, listed, actual, describe):
        for extra in sorted(listed - actual):
            violations.append({"rule": rule, "detail": f"{where} lists {describe(extra)}, which is not present in the repo"})
        for missing in sorted(actual - listed):
            violations.append({"rule": rule, "detail": f"{describe(missing)} is missing from {where}"})

    def name(skill):
        return f"skill `{skill}`"

    def edge(pair):
        return f"invocation `{pair[0]}` -> `{pair[1]}`"

    skills_md = open("SKILLS.md").read()
    compare(RULE_SKILLS_MD, "SKILLS.md",
            set(re.findall(r"^\|\s*\[`(\w+)`\]", skills_md, re.M)), skill_set, name)

    viz = open(os.path.join(".ai", "VIZ.md")).read()
    compare(RULE_VIZ, "the Skills table of .ai/VIZ.md",
            set(re.findall(r"^\|\s*\[`(\w+)`\]", viz, re.M)), skill_set, name)
    compare(RULE_VIZ, "the SkillInvocations table of .ai/VIZ.md",
            set(re.findall(r"^\|\s*`(\w+)`\s*\|\s*`(\w+)`\s*\|", viz, re.M)), edges, edge)

    diagram = re.search(r"```mermaid\n(.*?)```", viz, re.S)
    if not diagram:
        violations.append({"rule": RULE_VIZ, "detail": ".ai/VIZ.md contains no Mermaid diagram"})
    else:
        body = diagram.group(1)
        mermaid_edges = set(re.findall(r"(\w+)(?:\[[^\]]*\])?\s*-->\s*(\w+)", body))
        mermaid_nodes = {node for pair in mermaid_edges for node in pair} | set(re.findall(r"^\s*(\w+)\[", body, re.M))
        compare(RULE_VIZ, "the Mermaid diagram of .ai/VIZ.md", mermaid_nodes, skill_set, name)
        compare(RULE_VIZ, "the Mermaid diagram of .ai/VIZ.md", mermaid_edges, edges, edge)

    print(json.dumps({
        "skills": skills,
        "invocations": [list(pair) for pair in sorted(edges)],
        "violations": violations,
    }, indent=2))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
