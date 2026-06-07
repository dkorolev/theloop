---
name: ValidateSkill
description: Meta-skill that validates another skill in this repository against RULES.md. Takes a SkillRunId and the name of the skill to check; errors if the target skill does not exist, otherwise reports whether it complies with every rule.
argument-hint: <SkillRunId> <SkillNameToCheck>
---

# ValidateSkill

**Run receipt (do this no matter how this skill ends):** as the result of running this skill — success, validation failure, or error — you must write the file `tmp/<SkillRunId>.txt` (relative to the repository root), where `SkillRunId` is the first parameter of this skill. The file must contain exactly one well-formed JSON object following the schema in the "Run receipt schema" section below. Create the `tmp/` directory if it does not exist.

## Parameters

1. `SkillRunId` — a random identifier for this run, supplied by the caller. Used as the run-receipt filename: `tmp/<SkillRunId>.txt`.
2. `SkillNameToCheck` — the name of the other skill in this repository to validate.

If either parameter is missing, stop and report an error (and still write the run receipt with `"status": "error"`).

## Steps

1. **Confirm the target skill exists.** Look for `.claude/skills/<SkillNameToCheck>/SKILL.md` in this repository. If it does not exist, this run is an error: report it to the user, write the run receipt with `"status": "error"` and an explanatory `"error"` message, and stop.
2. **Read the rules.** Read `RULES.md` at the repository root. Every rule in that file applies to the target skill.
3. **Validate.** Read the target skill's `SKILL.md` and check it against each rule in `RULES.md`. For Rule 1 (run receipt), verify that the target skill:
   - declares `SkillRunId` as a parameter;
   - **begins** its instruction body with the instruction to write `tmp/<SkillRunId>.txt` upon completion;
   - **ends** its instruction body with that same instruction;
   - describes the JSON schema of the object written to `tmp/<SkillRunId>.txt`.
4. **Report.** Tell the user whether the skill passes, listing each violation (rule and detail) if it does not.
5. **Write the run receipt** as described below.

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.txt` must have exactly these fields:

```json
{
  "skill_run_id": "string — the SkillRunId parameter, verbatim",
  "skill": "ValidateSkill",
  "checked_skill": "string|null — the SkillNameToCheck parameter, or null if it was missing",
  "status": "pass | fail | error",
  "violations": [
    { "rule": "string — rule identifier from RULES.md, e.g. 'Rule 1'", "detail": "string — what is violated and where" }
  ],
  "error": "string|null — set only when status is 'error' (e.g. target skill not found)"
}
```

- `status` is `"pass"` when the target skill exists and satisfies every rule (then `violations` is `[]` and `error` is `null`);
- `"fail"` when it exists but violates at least one rule (then `violations` is non-empty);
- `"error"` when validation could not be performed at all (then `error` explains why).

**Run receipt (final reminder):** before finishing this skill — regardless of outcome — write `tmp/<SkillRunId>.txt` containing a single well-formed JSON object conforming to the schema above.
