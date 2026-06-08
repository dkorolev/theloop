---
name: InternalSkillPreCommitForClientWithRunId
description: Meta-skill that performs the slim pre-commit gate for a theloop client repository under a caller-supplied run identifier. Takes a single SkillRunId; checks receipt hygiene and runs the checks described in the repo-root PRECOMMIT.md. It does not check directory rules or validate skills — those are theloop-repo concerns.
argument-hint: <SkillRunId>
---

# InternalSkillPreCommitForClientWithRunId

**Run receipt (write once, never overwrite):** before doing anything else, check whether the file `tmp/<SkillRunId>.json` (relative to the repository root) already exists, where `SkillRunId` is the single parameter of this skill. If it exists, refuse to run: report the error to the user and stop without touching the file. Otherwise, no matter how this skill ends — success, check failure, or error — you must write `tmp/<SkillRunId>.json` containing exactly one well-formed JSON object following the schema in the "Run receipt schema" section below. Create the `tmp/` directory if it does not exist.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository. The git commands below operate on this repository's own index, which lives inside the repository directory.

## Parameters

This skill takes exactly one parameter:

1. `SkillRunId` — a random identifier for this run, supplied by the caller. Used as the run-receipt filename, `tmp/<SkillRunId>.json`. No file by that name may exist prior to the run. Typically the caller is `PreCommitSkill`, which generates the identifier in the default format codified in the rule on run receipts.

If the parameter is missing, or extra parameters are passed, stop and report an error (and still write the run receipt with `"status": "error"`, provided `tmp/<SkillRunId>.json` did not exist before the run).

## Scope

This skill is the slim, client-repo counterpart of the theloop repository's full pre-commit gate. It performs exactly two things — receipt hygiene and the checks described in `PRECOMMIT.md` — and deliberately omits the theloop-only concerns: directory rules, the rules registry, and skill meta-validation. Its checks are not content-determined (the `PRECOMMIT.md` commands typically run the repository's own tests), so the rule on hashing and caching of slow checks does not apply and nothing here is cached.

## Steps

All scripts under `.skills/InternalSkillPreCommitForClientWithRunId/scripts/` are executable and begin with `#!/usr/bin/env python3`; run each one directly by path — never prefix it with `python` or `python3`.

1. **Check the receipt hygiene.** The rule on run receipts requires that run receipts are never committed. Run `.skills/InternalSkillPreCommitForClientWithRunId/scripts/hygiene.py` from the repository root: it performs the three checks below and prints their outcomes as JSON, exiting non-zero when at least one fails. Record each check's outcome.
   - `tmp-gitignored` — the `tmp/` directory is gitignored;
   - `no-tracked-receipts` — no file under `tmp/` is tracked by git;
   - `no-staged-receipts` — no file under `tmp/` is staged.

2. **Run the `PRECOMMIT.md` checks.** If no `PRECOMMIT.md` exists at the root of the repository, record `extra_checks` as `null` and skip to the verdict. Otherwise read `PRECOMMIT.md` — a free-form Markdown file written by `theloop-post-setuprepo`. Interpreting that prose is a judgment call left to you: identify each check it describes and, for each, determine a short `check` name, the `directory` to run it from, and the exact `command` to execute. Write the resulting list to `tmp/<SkillRunId>-precommit-checks.json` as a JSON array of `{"check", "directory", "command"}` objects (an empty array when the file describes no runnable checks). Then run `.skills/InternalSkillPreCommitForClientWithRunId/scripts/run-checks.py --checks-file tmp/<SkillRunId>-precommit-checks.json` from the repository root: it runs each command from its directory and prints a JSON array of `{"check", "status", "detail"}` outcomes, exiting non-zero when at least one fails. Record that array as `extra_checks`.

3. **Verdict.** The commit may proceed — `"status": "pass"` — only when all three hygiene checks pass and every `PRECOMMIT.md` check passes (trivially true when no `PRECOMMIT.md` exists). Otherwise the commit must be blocked: `"status": "fail"` when at least one check fails, and `"status": "error"` when this skill could not perform the checks at all (bad parameters or a pre-existing receipt file).

4. **Report.** Tell the user the verdict: that the commit may proceed, or every reason it is blocked — each failing hygiene check and each failing `PRECOMMIT.md` check, with its detail.

5. **Write the run receipt** by calling `.skills/InternalSkillPreCommitForClientWithRunId/scripts/write-receipt.py` with CLI flags: `--skill-run-id`, `--hygiene-json JSON` (the JSON array output of `hygiene.py`), and `--extra-checks-json JSON` (the JSON array output of `run-checks.py`, or the string `null` when no `PRECOMMIT.md` exists). The script derives the overall status, validates the schema, and refuses to overwrite an existing receipt. For an error exit: `--status error --error TEXT` (with optional `--hygiene-json` if hygiene ran before the failure).

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.json` must have exactly these fields:

```json
{
  "skill_run_id": "string — the SkillRunId parameter, verbatim",
  "skill": "InternalSkillPreCommitForClientWithRunId",
  "status": "pass | fail | error",
  "hygiene_checks": [
    {
      "check": "tmp-gitignored | no-tracked-receipts | no-staged-receipts",
      "status": "pass | fail",
      "detail": "string|null — set only when the check fails: what is violated and where"
    }
  ],
  "extra_checks": [
    {
      "check": "string — a short name of a check described in PRECOMMIT.md",
      "status": "pass | fail",
      "detail": "string|null — set only when the check fails: what is violated and where"
    }
  ],
  "error": "string|null — set only when status is 'error' (e.g. missing parameter or a pre-existing receipt file)"
}
```

- `extra_checks` holds one entry per check described in `PRECOMMIT.md`; it is `null` when no `PRECOMMIT.md` exists at the root of the repository, and `[]` when `PRECOMMIT.md` exists but describes no runnable checks;
- `status` is `"pass"` when every entry of `hygiene_checks` has `"status": "pass"` and every entry of `extra_checks` (when not `null`) has `"status": "pass"` (then `error` is `null`);
- `"fail"` when the checks ran but at least one hygiene or extra check is not `"pass"` (then `error` is `null`);
- `"error"` when the checks could not be performed at all (then `hygiene_checks` contains whatever was gathered before the failure, possibly `[]`, `extra_checks` is `null`, and `error` explains why).

**Run receipt (final reminder):** before finishing this skill — regardless of outcome, success or error alike — write `tmp/<SkillRunId>.json` containing a single well-formed JSON object conforming to the schema above. The only exception is when `tmp/<SkillRunId>.json` already existed before the run: in that case refuse to run and never overwrite it.
