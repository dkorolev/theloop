---
name: ValidateSkill
description: Meta-skill that validates another skill in this repository against .ai/RULES.md. Takes a SkillRunId and the name of the skill to check; errors if the target skill does not exist, otherwise reports whether it complies with every rule.
argument-hint: <SkillRunId> <SkillNameToCheck>
---

# ValidateSkill

**Run receipt (write once, never overwrite):** before doing anything else, check whether the file `tmp/<SkillRunId>.json` (relative to the repository root) already exists, where `SkillRunId` is the first parameter of this skill. If it exists, refuse to run: report the error to the user and stop without touching the file. Otherwise, no matter how this skill ends — success, validation failure, or error — you must write `tmp/<SkillRunId>.json` containing exactly one well-formed JSON object following the schema in the "Run receipt schema" section below. Create the `tmp/` directory if it does not exist.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository.

## Parameters

This skill takes exactly two parameters, in this order:

1. `SkillRunId` — a random identifier for this run, supplied by the caller. Used as the run-receipt filename: `tmp/<SkillRunId>.json`. No file by that name may exist prior to the run.
2. `SkillNameToCheck` — the name of the other skill in this repository to validate.

If either parameter is missing, or extra parameters are passed, stop and report an error (and still write the run receipt with `"status": "error"`, provided `tmp/<SkillRunId>.json` did not exist before the run).

## Steps

1. **Confirm the target skill exists.** Look for `.skills/<SkillNameToCheck>/SKILL.md` in this repository. If it does not exist, this run is an error: report it to the user, write the run receipt with `"status": "error"` and an explanatory `"error"` message, and stop.
2. **Read the rules.** Read `.ai/RULES.md`, under the `.ai/` directory at the repository root. Every rule in that file applies to the target skill.
3. **Run the mechanical checks.** Run `.skills/ValidateSkill/scripts/mechanical-checks.py <SkillNameToCheck>` from the repository root. It checks the mechanically verifiable projections of the rules and prints the outcomes as JSON:
   - for the rule on containment within the repo, that the target skill states that running it is fully contained within the repository directory;
   - for the rule on run receipts, that the target skill declares `SkillRunId` as its first parameter or explicitly states that it is an exception that takes no `SkillRunId`; when it takes the parameter, that its instruction body **begins** and **ends** with the instruction to write but never overwrite `tmp/<SkillRunId>.json`, and that it describes the fixed JSON schema of that receipt; and when it generates a `SkillRunId` itself, rather than receiving it from its caller, that it prescribes the default format codified in that rule;
   - for the rule on the `SKILLS.md` file and the rule on visualization and topology, their per-skill projection: the target skill is listed in `SKILLS.md`, and is listed in `.ai/VIZ.md` together with all of its actual invocation relationships. Checking the other direction — that nothing extra is listed — is a whole-repo property and is out of scope for this single-skill check;
   - for the rule on referring to rules by name, that the target skill never references a rule by its number;
   - for the rule on use of scripts, that every script the target skill references exists at the referenced path.

   The script matches fixed phrasings, so confirm each reported failure against the target skill's text before recording it as a violation; treat compliant-but-differently-worded text as a reason to read closer, not as an automatic violation.
4. **Judge the remaining rules.** Read the target skill's `SKILL.md` and check what the script cannot:
   - For the rule on strict parameters, verify that the target skill declares exactly which parameters it takes and instructs the runner to validate them before executing, and that any invocations of other skills pass exactly the right parameters. In particular, verify that it refuses to run, with an error, if `tmp/<SkillRunId>.json` exists prior to the run.
   - For the rule on the universal directory for skills, note that the first step already enforces it structurally: a skill anywhere else than under `.skills/` is not found at all.
   - For the rule on use of scripts, verify that any non-trivial code the target skill runs is provided as scripts under `.skills/<SkillNameToCheck>/scripts/` rather than written as ad-hoc temporary files.
   - For the rule on taste and style, verify that the target skill's text is free of grammatical errors and easy to read, and that any provided scripts are understandable, follow simple input/output formats, perform no surprising operations, and keep their error messages short yet complete.
   - For the rule on parallel invocation of spawned skills, verify that if the target skill invokes other skills: when it starts two or more independent sub-runs, it instructs the runner to launch them concurrently and aggregate receipts after all complete; when parallel execution is undesirable, it explains in detail why; when it invokes exactly one other skill, no parallelism wording is required.
5. **Report.** Tell the user whether the skill passes, listing each violation (rule and detail) if it does not.
6. **Write the run receipt** as described below: assemble the receipt object and pipe it to `.skills/ValidateSkill/scripts/write-receipt.py`, which validates the schema and refuses to overwrite an existing receipt.

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.json` must have exactly these fields:

```json
{
  "skill_run_id": "string — the SkillRunId parameter, verbatim",
  "skill": "ValidateSkill",
  "checked_skill": "string|null — the SkillNameToCheck parameter, or null if it was missing",
  "status": "pass | fail | error",
  "violations": [
    { "rule": "string — the name of the violated rule, as it is titled in .ai/RULES.md", "detail": "string — what is violated and where" }
  ],
  "error": "string|null — set only when status is 'error' (e.g. target skill not found)"
}
```

- `status` is `"pass"` when the target skill exists and satisfies every rule (then `violations` is `[]` and `error` is `null`);
- `"fail"` when it exists but violates at least one rule (then `violations` is non-empty);
- `"error"` when validation could not be performed at all (then `error` explains why).

**Run receipt (final reminder):** before finishing this skill — regardless of outcome, success or error alike — write `tmp/<SkillRunId>.json` containing a single well-formed JSON object conforming to the schema above. The only exception is when `tmp/<SkillRunId>.json` already existed before the run: in that case refuse to run and never overwrite it.
