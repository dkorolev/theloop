---
name: ValidateAllSkills
description: Meta-skill that validates every skill in this repository against .ai/RULES.md. Takes a single SkillRunId; invokes ValidateSkill once per skill in parallel, then performs the whole-repo checks that SKILLS.md and .ai/VIZ.md exactly match the repository.
argument-hint: <SkillRunId>
invokes: [ValidateSkill]
---

# ValidateAllSkills

**Run receipt (write once, never overwrite):** before doing anything else, check whether the file `tmp/<SkillRunId>.json` (relative to the repository root) already exists, where `SkillRunId` is the single parameter of this skill. If it exists, refuse to run: report the error to the user and stop without touching the file. Otherwise, no matter how this skill ends — success, validation failure, or error — you must write `tmp/<SkillRunId>.json` containing exactly one well-formed JSON object following the schema in the "Run receipt schema" section below. Create the `tmp/` directory if it does not exist.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository.

## Parameters

This skill takes exactly one parameter:

1. `SkillRunId` — a random identifier for this run, supplied by the caller. Used as the run-receipt filename, `tmp/<SkillRunId>.json`, and as the prefix of the sub-run identifiers passed to `ValidateSkill`. No file by that name may exist prior to the run.

If the parameter is missing, or extra parameters are passed, stop and report an error (and still write the run receipt with `"status": "error"`, provided `tmp/<SkillRunId>.json` did not exist before the run).

## Steps

All scripts under `.skills/ValidateAllSkills/scripts/` are executable and begin with `#!/usr/bin/env python3`; run each one directly by path — never prefix it with `python` or `python3`.

1. **Enumerate the skills and run the whole-repo checks.** Run `.skills/ValidateAllSkills/scripts/repo-checks.py` from the repository root. It enumerates the skills of this repository — exactly the directories `.skills/<SkillName>/` that contain a `SKILL.md` file — extracts the invocation relationships that actually exist from the skills' `SKILL.md` files, performs the whole-repo checks described in the fourth step, and prints the skills, the relationships, and any violations as JSON. If it reports that no skills exist, this run is an error: report it, write the run receipt with `"status": "error"`, and stop.
2. **Check the sub-run preconditions.** For each `<SkillName>`, the sub-run identifier is `<SkillRunId>-<SkillName>`. If the file `tmp/<SkillRunId>-<SkillName>.json` already exists for any skill, this run is an error: report which files are in the way, write the run receipt with `"status": "error"`, and stop before validating anything.
3. **Validate each skill.** Per the rule on parallel invocation of spawned skills, launch every `ValidateSkill` sub-run concurrently — each `<SkillName>` from step 1, including `ValidateSkill` and this very skill, gets its own sub-run with identifier `<SkillRunId>-<SkillName>` checked in step 2. For each, invoke `ValidateSkill` with exactly two parameters, in this order: the sub-run identifier `<SkillRunId>-<SkillName>`, and `<SkillName>`. Invoke through the configured skill runner if one is available; otherwise execute by reading `.skills/ValidateSkill/SKILL.md` and following its instructions literally. As each sub-run completes, report its outcome using the phrasing "Validation of skill `<SkillName>` succeeded." or "Validation of skill `<SkillName>` failed." — not just "`<SkillName>` passed/failed", which is ambiguous when the skill's execution and its validation are both in flight at the same time. After all sub-runs have completed, read each sub-run receipt `tmp/<SkillRunId>-<SkillName>.json` and record its `status`, `source`, and `violations`. The sub-run receipts are write-once like any run receipt: leave them in place, never overwrite or delete them.
4. **Record the whole-repo checks.** These are the checks that `ValidateSkill` declares out of scope for a single-skill run, because they are properties of the repository as a whole; the script from the first step has already performed them:
   - For the rule on the `SKILLS.md` file: `SKILLS.md` lists exactly the skills enumerated in the first step — every skill in the repo appears in `SKILLS.md`, and every skill listed in `SKILLS.md` exists in the repo.
   - For the rule on visualization and topology: `.ai/VIZ.md` lists exactly the skills enumerated in the first step, and exactly the invocation relationships that actually exist. Also, the Mermaid diagram in `.ai/VIZ.md` contains exactly the same skills as nodes and the same invocation relationships as arrows as the two tables do.

   The script reads the `invokes` field from each skill's `SKILL.md` frontmatter to build the set of actual invocation relationships. Record every violation the script reports as a pair of the rule's name, as it is titled in `.ai/RULES.md`, and a detail of what is violated and where.
5. **Report.** Tell the user whether the repository passes: `"pass"` when every sub-run reports `"pass"` and the whole-repo checks find no violations; `"fail"` when at least one sub-run reports `"fail"` or `"error"`, or at least one whole-repo violation is found; `"error"` when this skill could not perform the validation at all (bad parameters, a pre-existing receipt file, or no skills found). List each failing skill and each violation.
6. **Write the run receipt** by calling `.skills/ValidateAllSkills/scripts/write-receipt.py` with CLI flags: `--skill-run-id` and `--sub-run-ids "id1 id2 ..."` listing every `ValidateSkill` sub-run identifier separated by spaces; optionally `--repo-violations-json '[...]'` (defaults to `[]`). The script reads the sub-run receipts, derives the overall status, computes `cache_summary`, validates the schema, and refuses to overwrite an existing receipt. For an error exit: `--status error --error TEXT` (omit `--sub-run-ids`).

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.json` must have exactly these fields:

```json
{
  "skill_run_id": "string — the SkillRunId parameter, verbatim",
  "skill": "ValidateAllSkills",
  "status": "pass | fail | error",
  "skills_checked": [
    {
      "skill": "string — the name of the validated skill",
      "sub_run_id": "string — the sub-run identifier passed to ValidateSkill",
      "status": "pass | fail | error — as reported by the sub-run receipt",
      "source": "cache | regenerated | null — as reported by the sub-run receipt; null when status is error",
      "violations": [
        { "rule": "string — the name of the violated rule, as it is titled in .ai/RULES.md", "detail": "string — what is violated and where" }
      ]
    }
  ],
  "repo_violations": [
    { "rule": "string — the name of the violated rule, as it is titled in .ai/RULES.md", "detail": "string — what is violated and where" }
  ],
  "cache_summary": {
    "cached": "integer — count of skills_checked entries whose source is cache",
    "regenerated": "integer — count of skills_checked entries whose source is regenerated"
  },
  "error": "string|null — set only when status is 'error' (e.g. missing parameter or a pre-existing receipt file)"
}
```

- `cache_summary` counts how many skill validations were served from the cache versus re-run in full; its counts must match `skills_checked`;
- `status` is `"pass"` when every entry of `skills_checked` has `"status": "pass"` and `repo_violations` is `[]` (then `error` is `null`);
- `"fail"` when validation ran but at least one entry of `skills_checked` has a status other than `"pass"`, or `repo_violations` is non-empty (then `error` is `null`);
- `"error"` when validation could not be performed at all (then `skills_checked` and `repo_violations` contain whatever was gathered before the failure, possibly `[]`, and `error` explains why).

**Run receipt (final reminder):** before finishing this skill — regardless of outcome, success or error alike — write `tmp/<SkillRunId>.json` containing a single well-formed JSON object conforming to the schema above. The only exception is when `tmp/<SkillRunId>.json` already existed before the run: in that case refuse to run and never overwrite it.
