---
name: ValidateAllSkills
description: Meta-skill that validates every skill in this repository against RULES.md. Takes a single SkillRunId; invokes ValidateSkill once per skill in parallel, then performs the whole-repo checks that SKILLS.md and VIZ.md exactly match the repository.
argument-hint: <SkillRunId>
---

# ValidateAllSkills

**Run receipt (write once, never overwrite):** before doing anything else, check whether the file `tmp/<SkillRunId>.json` (relative to the repository root) already exists, where `SkillRunId` is the single parameter of this skill. If it exists, refuse to run: report the error to the user and stop without touching the file. Otherwise, no matter how this skill ends — success, validation failure, or error — you must write `tmp/<SkillRunId>.json` containing exactly one well-formed JSON object following the schema in the "Run receipt schema" section below. Create the `tmp/` directory if it does not exist.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository.

## Parameters

This skill takes exactly one parameter:

1. `SkillRunId` — a random identifier for this run, supplied by the caller. Used as the run-receipt filename, `tmp/<SkillRunId>.json`, and as the prefix of the sub-run identifiers passed to `ValidateSkill`. No file by that name may exist prior to the run.

If the parameter is missing, or extra parameters are passed, stop and report an error (and still write the run receipt with `"status": "error"`, provided `tmp/<SkillRunId>.json` did not exist before the run).

## Steps

1. **Enumerate the skills.** The skills of this repository are exactly the directories `.skills/<SkillName>/` that contain a `SKILL.md` file. If there are none, this run is an error: report it, write the run receipt with `"status": "error"`, and stop.
2. **Check the sub-run preconditions.** For each `<SkillName>`, the sub-run identifier is `<SkillRunId>-<SkillName>`. If the file `tmp/<SkillRunId>-<SkillName>.json` already exists for any skill, this run is an error: report which files are in the way, write the run receipt with `"status": "error"`, and stop before validating anything.
3. **Validate each skill.** Per the rule on parallel invocation of spawned skills, launch every `ValidateSkill` sub-run concurrently — each `<SkillName>` from step 1, including `ValidateSkill` and this very skill, gets its own sub-run with identifier `<SkillRunId>-<SkillName>` checked in step 2. For each, invoke `ValidateSkill` with exactly two parameters, in this order: the sub-run identifier `<SkillRunId>-<SkillName>`, and `<SkillName>`. Invoke through the configured skill runner if one is available; otherwise execute by reading `.skills/ValidateSkill/SKILL.md` and following its instructions literally. After all sub-runs have completed, read each sub-run receipt `tmp/<SkillRunId>-<SkillName>.json` and record its `status` and `violations`. The sub-run receipts are write-once like any run receipt: leave them in place, never overwrite or delete them.
4. **Perform the whole-repo checks.** These are the checks that `ValidateSkill` declares out of scope for a single-skill run, because they are properties of the repository as a whole:
   - For the rule on the `SKILLS.md` file: `SKILLS.md` lists exactly the skills enumerated in the first step — every skill in the repo appears in `SKILLS.md`, and every skill listed in `SKILLS.md` exists in the repo.
   - For the rule on visualization and topology: `VIZ.md` lists exactly the skills enumerated in the first step, and exactly the invocation relationships that actually exist — determine the actual relationships by reading every skill's `SKILL.md` and noting which other skills it invokes. Also check that the Mermaid diagram in `VIZ.md` contains exactly the same skills as nodes and the same invocation relationships as arrows as the two tables do.

   Record every violation found here as a pair of the rule's name, as it is titled in `RULES.md`, and a detail of what is violated and where.
5. **Report.** Tell the user whether the repository passes: `"pass"` when every sub-run reports `"pass"` and the whole-repo checks find no violations; `"fail"` when at least one sub-run reports `"fail"` or `"error"`, or at least one whole-repo violation is found; `"error"` when this skill could not perform the validation at all (bad parameters, a pre-existing receipt file, or no skills found). List each failing skill and each violation.
6. **Write the run receipt** as described below.

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
      "violations": [
        { "rule": "string — the name of the violated rule, as it is titled in RULES.md", "detail": "string — what is violated and where" }
      ]
    }
  ],
  "repo_violations": [
    { "rule": "string — the name of the violated rule, as it is titled in RULES.md", "detail": "string — what is violated and where" }
  ],
  "error": "string|null — set only when status is 'error' (e.g. missing parameter or a pre-existing receipt file)"
}
```

- `status` is `"pass"` when every entry of `skills_checked` has `"status": "pass"` and `repo_violations` is `[]` (then `error` is `null`);
- `"fail"` when validation ran but at least one entry of `skills_checked` has a status other than `"pass"`, or `repo_violations` is non-empty (then `error` is `null`);
- `"error"` when validation could not be performed at all (then `skills_checked` and `repo_violations` contain whatever was gathered before the failure, possibly `[]`, and `error` explains why).

**Run receipt (final reminder):** before finishing this skill — regardless of outcome, success or error alike — write `tmp/<SkillRunId>.json` containing a single well-formed JSON object conforming to the schema above. The only exception is when `tmp/<SkillRunId>.json` already existed before the run: in that case refuse to run and never overwrite it.
