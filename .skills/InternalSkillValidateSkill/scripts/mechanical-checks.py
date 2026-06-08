#!/usr/bin/env python3
"""Mechanical rule checks of InternalSkillValidateSkill against one target skill.

Usage: .skills/InternalSkillValidateSkill/scripts/mechanical-checks.py <SkillNameToCheck>   (from the repository root)
Checks the mechanically verifiable projections of the rules in .theloop/SKILLS-META-RULES.md
against .skills/<SkillNameToCheck>/SKILL.md; the judgment-based rules (strict
parameter semantics, taste and style, fan-out subagents wording) are left to
the agentic runner.
Output: one JSON object {"skill", "checks"} on stdout, where each check is
{"rule", "check", "status", "detail"}; "rule" is the rule's name as titled in
.theloop/SKILLS-META-RULES.md and "detail" is null unless the check fails.
Exit code: 0 when all checks pass, 1 when at least one fails, 2 when the target
skill does not exist or the usage is wrong (then {"error": ...} is printed).
"""
import json
import os
import re
import sys

RULE_CONTAINED = "Contained within the repo"
RULE_RECEIPTS = "Strict with output in the form of Run Receipts"
RULE_SKILLS_MD = "The `SKILLS.md` file should be up to date"
RULE_VIZ = "Visualization and topology"
RULE_SCRIPTS = "Use of scripts"
RULE_BY_NAME = "Refer to rules by name, not by number"
RULE_INTERNAL_NAMING = "Internal skill naming"
INTERNAL_PREFIX = "InternalSkill"


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: mechanical-checks.py <SkillNameToCheck>"}))
        return 2
    skill = sys.argv[1]
    path = f".skills/{skill}/SKILL.md"
    if not os.path.isfile(path):
        print(json.dumps({"error": f"{path} not found: no such skill"}))
        return 2

    body = re.sub(r"\A---\n.*?\n---\n", "", open(path).read(), flags=re.S)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    if paragraphs and paragraphs[0].startswith("# "):
        paragraphs = paragraphs[1:]

    checks = []

    def add(rule, check, ok, detail):
        checks.append({"rule": rule, "check": check, "status": "pass" if ok else "fail",
                       "detail": None if ok else detail})

    add(RULE_CONTAINED, "containment-stated",
        "contained within the directory of" in body and "outside the repository" in body,
        f"{path} does not state that the run is fully contained within the repository directory")

    def has_receipt_instruction(paragraph):
        return "tmp/<SkillRunId>.json" in paragraph and "writ" in paragraph.lower()

    takes_run_id = re.search(r"^\s*1\.\s+`SkillRunId`", body, re.M) is not None
    if takes_run_id:
        add(RULE_INTERNAL_NAMING, "internal-prefix-required", skill.startswith(INTERNAL_PREFIX),
            f"{path} takes SkillRunId but its name does not begin with {INTERNAL_PREFIX}")
    else:
        add(RULE_INTERNAL_NAMING, "no-internal-prefix", not skill.startswith(INTERNAL_PREFIX),
            f"{path} does not take SkillRunId but its name begins with {INTERNAL_PREFIX}")
    if takes_run_id:
        add(RULE_RECEIPTS, "receipt-instruction-first", has_receipt_instruction(paragraphs[0]),
            f"{path} does not begin its body with the write-once receipt instruction")
        add(RULE_RECEIPTS, "receipt-instruction-last", has_receipt_instruction(paragraphs[-1]),
            f"{path} does not end its body with the write-once receipt instruction")
        add(RULE_RECEIPTS, "receipt-schema-described", '"skill_run_id"' in body,
            f"{path} does not describe the JSON schema of its run receipt")
    else:
        add(RULE_RECEIPTS, "exception-stated",
            re.search(r"exception\w*[^\n]*`SkillRunId`", body) is not None,
            f"{path} neither declares `SkillRunId` as its first parameter nor states that it is the exception that takes none")
        if re.search(r"[Gg]enerate", body) and "`SkillRunId`" in body:
            add(RULE_RECEIPTS, "default-id-format", "YYYYMMDD-HHMMSS" in body,
                f"{path} generates a `SkillRunId` but does not prescribe the default format")

    skills_md = open("SKILLS.md").read()
    add(RULE_SKILLS_MD, "listed-in-skills-md", f"[`{skill}`]" in skills_md,
        f"`{skill}` is not listed in SKILLS.md")

    viz = open(os.path.join(".theloop", "VIZ.md")).read()
    add(RULE_VIZ, "listed-in-viz-md", f"[`{skill}`]" in viz,
        f"`{skill}` is not listed in the Skills table of .theloop/VIZ.md")

    fm_match = re.match(r"^---\n(.*?)\n---\n", open(path).read(), re.S)
    invoked = []
    if fm_match:
        inv = re.search(r"^invokes:\s*\[([^\]]*)\]", fm_match.group(1), re.M)
        if inv:
            all_skills = {d for d in os.listdir(".skills") if os.path.isfile(os.path.join(".skills", d, "SKILL.md"))}
            invoked = [s.strip() for s in inv.group(1).split(",") if s.strip() and s.strip() in all_skills and s.strip() != skill]
    for other in sorted(invoked):
        add(RULE_VIZ, f"invocation-listed-{other}",
            re.search(rf"^\|\s*`{skill}`\s*\|\s*`{other}`\s*\|", viz, re.M) is not None,
            f"the invocation `{skill}` -> `{other}` is missing from the SkillInvocations table of .theloop/VIZ.md")

    number_ref = re.search(r"\bRule\s+\d", body)
    add(RULE_BY_NAME, "no-rule-numbers", number_ref is None,
        f'{path} refers to a rule by number ("{number_ref.group(0)}")' if number_ref else None)

    for owner, script in sorted(set(re.findall(r"\.skills/([\w-]+)/scripts/([\w.-]+\.(?:py|sh))", body))):
        add(RULE_SCRIPTS, f"script-exists-{script}",
            os.path.isfile(f".skills/{owner}/scripts/{script}"),
            f"{path} references .skills/{owner}/scripts/{script}, which does not exist")

    has_write_receipt = os.path.isfile(f".skills/{skill}/scripts/write-receipt.py")
    if takes_run_id:
        add(RULE_SCRIPTS, "write-receipt-script-present", has_write_receipt,
            f"{path} takes SkillRunId but has no write-receipt.py under .skills/{skill}/scripts/")
    if has_write_receipt:
        add(RULE_SCRIPTS, "receipt-written-via-cli", "--skill-run-id" in body,
            f"{path} has write-receipt.py but does not instruct the runner to call it with --skill-run-id CLI flags")

    print(json.dumps({"skill": skill, "checks": checks}, indent=2))
    return 0 if all(c["status"] == "pass" for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
