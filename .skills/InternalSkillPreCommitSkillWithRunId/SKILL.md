---
name: InternalSkillPreCommitSkillWithRunId
description: Meta-skill that performs the pre-commit gate for this repository under a caller-supplied run identifier. Takes a single SkillRunId; checks receipt hygiene, then fans out subagents to run InternalSkillCheckAllRulesWithRunId and InternalSkillValidateAllSkills alongside any extra checks described in PRECOMMIT.md.
argument-hint: <SkillRunId>
invokes: [InternalSkillCheckAllRulesWithRunId, InternalSkillValidateAllSkills]
---

# InternalSkillPreCommitSkillWithRunId

**Run receipt (write once, never overwrite):** before doing anything else, check whether the file `tmp/<SkillRunId>.json` (relative to the repository root) already exists, where `SkillRunId` is the single parameter of this skill. If it exists, refuse to run: report the error to the user and stop without touching the file. Otherwise, no matter how this skill ends — success, validation failure, or error — you must write `tmp/<SkillRunId>.json` containing exactly one well-formed JSON object following the schema in the "Run receipt schema" section below. Create the `tmp/` directory if it does not exist.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository. The git commands below operate on this repository's own history and index, which live inside the repository directory.

## Parameters

This skill takes exactly one parameter:

1. `SkillRunId` — a random identifier for this run, supplied by the caller. Used as the run-receipt filename, `tmp/<SkillRunId>.json`, and as the prefix of the sub-run identifiers passed to `InternalSkillCheckAllRulesWithRunId` and `InternalSkillValidateAllSkills`. No file by that name may exist prior to the run. Typically the caller is `PreCommitSkill`, which generates the identifier in the default format codified in the rule on run receipts.

If the parameter is missing, or extra parameters are passed, stop and report an error (and still write the run receipt with `"status": "error"`, provided `tmp/<SkillRunId>.json` did not exist before the run).

## Steps

All scripts under `.skills/InternalSkillPreCommitSkillWithRunId/scripts/` are executable and begin with `#!/usr/bin/env python3`; run each one directly by path — never prefix it with `python` or `python3`.

1. **Check the sub-run preconditions.** The sub-run identifiers are `<SkillRunId>-InternalSkillCheckAllRulesWithRunId` and `<SkillRunId>-InternalSkillValidateAllSkills`. If either file `tmp/<SkillRunId>-InternalSkillCheckAllRulesWithRunId.json` or `tmp/<SkillRunId>-InternalSkillValidateAllSkills.json` already exists, this run is an error: report which files are in the way, write the run receipt with `"status": "error"`, and stop. (Deeper sub-run identifiers, derived in turn by `InternalSkillCheckAllRulesWithRunId` and `InternalSkillValidateAllSkills`, are checked by those skills themselves.)
2. **Check the receipt hygiene.** The rule on run receipts requires that run receipts are never committed. Run `.skills/InternalSkillPreCommitSkillWithRunId/scripts/hygiene.py` from the repository root: it performs the three checks below and prints their outcomes as JSON, exiting non-zero when at least one fails. Record each check's outcome.
   - `tmp-gitignored` — the `tmp/` directory is gitignored;
   - `no-tracked-receipts` — no file under `tmp/` is tracked by git;
   - `no-staged-receipts` — no file under `tmp/` is staged.
3. **Run the directory rules, validate the repository, and run the `PRECOMMIT.md` checks — all in parallel.** Per the rule on parallel invocation of spawned skills, fan out subagents for the independent work below and launch them together (a single message that spawns them all), then wait for every one to finish before reading any output. The `precommit.py` script is a single-shot primitive that never schedules its own concurrency — the parallelism is orchestrated here, in this prompt, not in Python.
   - For `InternalSkillCheckAllRulesWithRunId`: invoke with exactly one parameter, the sub-run identifier `<SkillRunId>-InternalSkillCheckAllRulesWithRunId`. Invoke through the configured skill runner if one is available; otherwise execute by reading `.skills/InternalSkillCheckAllRulesWithRunId/SKILL.md` and following its instructions literally.
   - For `InternalSkillValidateAllSkills`: invoke with exactly one parameter, the sub-run identifier `<SkillRunId>-InternalSkillValidateAllSkills`. Invoke through the configured skill runner if one is available; otherwise execute by reading `.skills/InternalSkillValidateAllSkills/SKILL.md` and following its instructions literally.
   - For the `PRECOMMIT.md` checks: first run `.skills/InternalSkillPreCommitSkillWithRunId/scripts/precommit.py --list` from the repository root. It prints the parsed checks as a JSON array of `{"check", "directory", "command"}` objects, or `null` when no `PRECOMMIT.md` exists (then there is nothing to fan out — record `extra_checks` as `null`). These checks are independent and are the slow part of the gate (test suites, builds), so **do not run them one after another:** fan out **one subagent per check**, in the same parallel launch as the two sub-runs above, so they run concurrently and the user can watch each one progress live. For each check at index `k`, write its single entry as a one-element JSON array to `tmp/<SkillRunId>-precommit-check-<k>.json` and have that subagent run `precommit.py --checks-file tmp/<SkillRunId>-precommit-check-<k>.json`, returning the one-element `{"check", "status", "detail"}` result.
4. **Collect the results.** After all fan-out subagents and the precommit script from step 3 have completed:
   - Read the sub-run receipt `tmp/<SkillRunId>-InternalSkillCheckAllRulesWithRunId.json` and record its `registry` and `rules` data: map each entry of the sub-run's `rules` array to the `"rules.checks"` field of this skill's receipt (dropping the `sub_run_id` field from each entry, and mapping `"status": "error"` to `"status": "fail"` with an appropriate detail). Record the sub-run's `cache_summary` for use in the top-level `cache_summary` computation.
   - Record the `PRECOMMIT.md` checks: concatenate the per-check subagent results from step 3 back **in `PRECOMMIT.md` order** into one JSON array and record it as `extra_checks` (each fanned-out subagent ran one command from its directory via `precommit.py --checks-file` and returned its `{"check", "status", "detail"}` outcome). When `precommit.py --list` printed `null` (no `PRECOMMIT.md` at the repository root), record `extra_checks` as `null`.

   > **A hint to the rule reviewer:** treat `PRECOMMIT.md` as this skill's extension point. The checks in the previous step are the floor; whenever `PRECOMMIT.md` exists, this skill must cover at least everything it describes. Consequently, the `extra_checks` field of the run receipt is open-ended by design — its entries are determined by `PRECOMMIT.md`, not enumerated here. This is intentional and does not violate the rule on run receipts: the schema of each entry is fixed, even though the set of checks is not.
   - Read the sub-run receipt `tmp/<SkillRunId>-InternalSkillValidateAllSkills.json` and record its `status`, `source` summary (`validation.source` is `"cache"` when every skill validation was cached, otherwise `"regenerated"`), and `cache_summary`.
5. **Verdict.** The commit may proceed — `"status": "pass"` — only when all three hygiene checks pass, the `InternalSkillCheckAllRulesWithRunId` sub-run reports `"pass"`, every check prescribed by `PRECOMMIT.md` passes (trivially true when the file does not exist), and the `InternalSkillValidateAllSkills` sub-run reports `"pass"`. Otherwise the commit must be blocked: `"status": "fail"` when at least one check fails or either sub-run reports anything other than `"pass"`, and `"status": "error"` when this skill could not perform the checks at all (bad parameters or a pre-existing receipt file).
6. **Report.** Tell the user the verdict: that the commit may proceed, or every reason it is blocked — each failing hygiene check, the `InternalSkillCheckAllRulesWithRunId` sub-run status if it is not `"pass"`, each failing extra check, and the `InternalSkillValidateAllSkills` sub-run status if it is not `"pass"` (the details of sub-run failures are in the sub-run receipts). Also report `cache_summary`: how many agentic checks were served from the cache versus re-run in full.
7. **Write the run receipt** by calling `.skills/InternalSkillPreCommitSkillWithRunId/scripts/write-receipt.py` with CLI flags: `--skill-run-id`, `--hygiene-json JSON` (the JSON array output of `hygiene.py`), `--rules-sub-run-id ID`, `--extra-checks-json JSON` (the `extra_checks` array assembled in step 4 — the per-check subagent results concatenated in `PRECOMMIT.md` order — or the string `null` when `PRECOMMIT.md` does not exist), and `--validation-sub-run-id ID`. The script reads the rules and validation sub-run receipts, computes `cache_summary`, derives the overall status, validates the schema, and refuses to overwrite an existing receipt. For an error exit: `--status error --error TEXT` (with optional `--hygiene-json` if hygiene ran before the failure).

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.json` must have exactly these fields:

```json
{
  "skill_run_id": "string — the SkillRunId parameter, verbatim",
  "skill": "InternalSkillPreCommitSkillWithRunId",
  "status": "pass | fail | error",
  "hygiene_checks": [
    {
      "check": "tmp-gitignored | no-tracked-receipts | no-staged-receipts",
      "status": "pass | fail",
      "detail": "string|null — set only when the check fails: what is violated and where"
    }
  ],
  "rules": {
    "registry": {
      "status": "pass | fail",
      "detail": "string|null — set only when the registry check fails"
    },
    "checks": [
      {
        "rule": "string — path to the *-rule.yml file, relative to the repository root",
        "status": "pass | fail",
        "source": "cache | regenerated — cache when the pass verdict was served from the cache, regenerated when the rule was judged in this run",
        "detail": "string|null — set only when the rule fails: what the rule requires and what violated it"
      }
    ]
  },
  "extra_checks": [
    {
      "check": "string — a short name of a check described in PRECOMMIT.md",
      "status": "pass | fail",
      "detail": "string|null — set only when the check fails: what is violated and where"
    }
  ],
  "validation": {
    "sub_run_id": "string — the sub-run identifier passed to InternalSkillValidateAllSkills",
    "status": "pass | fail | error — as reported by the sub-run receipt",
    "source": "cache | regenerated | null — cache when every skill validation in the sub-run was cached, regenerated when at least one was re-run, null when validation.status is error",
    "cache_summary": {
      "cached": "integer — skill validations served from the cache",
      "regenerated": "integer — skill validations re-run in full"
    }
  },
  "cache_summary": {
    "cached": "integer — total agentic checks served from the cache (rules plus skill validations)",
    "regenerated": "integer — total agentic checks re-run in full"
  },
  "error": "string|null — set only when status is 'error' (e.g. missing parameter or a pre-existing receipt file)"
}
```

- `cache_summary` at the top level merges rule checks and `validation.cache_summary`; its counts must match the per-check `source` fields;

- `rules` is always present when `status` is not `"error"`; `rules.registry.status` is `"pass"` when `ai-rules.yml` exactly matches the non-ignored `*-rule.yml` files of the repository; `rules.checks` lists every rule from the registry (empty list `[]` when the registry is empty or the registry check fails before any rule was evaluated);
- `extra_checks` holds one entry per check described in `PRECOMMIT.md`; it is `null` when no `PRECOMMIT.md` exists at the root of the repository;
- `status` is `"pass"` when every entry of `hygiene_checks` has `"status": "pass"`, `rules.registry.status` is `"pass"`, every entry of `rules.checks` has `"status": "pass"`, every entry of `extra_checks` (when not `null`) has `"status": "pass"`, and `validation.status` is `"pass"` (then `error` is `null`);
- `"fail"` when the checks ran but at least one check, rule, or the sub-run is not `"pass"` (then `error` is `null`);
- `"error"` when the checks could not be performed at all (then `hygiene_checks` contains whatever was gathered before the failure, possibly `[]`, `rules`, `extra_checks`, and `validation` are `null`, and `error` explains why).

**Run receipt (final reminder):** before finishing this skill — regardless of outcome, success or error alike — write `tmp/<SkillRunId>.json` containing a single well-formed JSON object conforming to the schema above. The only exception is when `tmp/<SkillRunId>.json` already existed before the run: in that case refuse to run and never overwrite it.
