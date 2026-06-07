---
name: CheckAllInvariantsWithRunId
description: Meta-skill that checks all directory invariants listed in ai-invariants.yml. Takes a single SkillRunId; verifies the registry, then invokes CheckSingleInvariantWithRunId once per invariant in parallel (each handles its own caching per .ai/CACHING.md).
argument-hint: <SkillRunId>
---

# CheckAllInvariantsWithRunId

**Run receipt (write once, never overwrite):** before doing anything else, check whether the file `tmp/<SkillRunId>.json` (relative to the repository root) already exists, where `SkillRunId` is the single parameter of this skill. If it exists, refuse to run: report the error to the user and stop without touching the file. Otherwise, no matter how this skill ends — success, validation failure, or error — you must write `tmp/<SkillRunId>.json` containing exactly one well-formed JSON object following the schema in the "Run receipt schema" section below. Create the `tmp/` directory if it does not exist.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository.

## Parameters

This skill takes exactly one parameter:

1. `SkillRunId` — a random identifier for this run, supplied by the caller. Used as the run-receipt filename, `tmp/<SkillRunId>.json`, and as the prefix of the sub-run identifiers passed to `CheckSingleInvariantWithRunId`. No file by that name may exist prior to the run.

If the parameter is missing, or extra parameters are passed, stop and report an error (and still write the run receipt with `"status": "error"`, provided `tmp/<SkillRunId>.json` did not exist before the run).

## Steps

1. **Check the registry and enumerate invariants.** Run `.skills/CheckAllInvariantsWithRunId/scripts/invariants.py probe` from the repository root. The script verifies that `ai-invariants.yml` lists exactly the non-ignored `*-INVARIANT.md` files of the repository, fingerprints each invariant's directory subtree per `.ai/CACHING.md`, and reports the registry status and the full list of invariants — each with its path and the `sub_run_suffix` to use when forming its sub-run identifier.
   - If the registry check fails (unlisted invariant files or listed paths that do not exist), this is a blocking failure: record `registry.status = "fail"` with the detail, set `invariants = []`, and proceed to the verdict without running any invariant.
   - If the registry check passes and no invariants are listed, `invariants = []` and proceed to the verdict.

2. **Check the sub-run preconditions.** For each invariant, the sub-run identifier is `<SkillRunId>-<sub_run_suffix>`, where `sub_run_suffix` is the value provided by the script for that invariant. If the file `tmp/<SkillRunId>-<sub_run_suffix>.json` already exists for any invariant, this run is an error: report which files are in the way, write the run receipt with `"status": "error"`, and stop before invoking any sub-run.

3. **Check each invariant.** Per the rule on parallel invocation of spawned skills, launch every `CheckSingleInvariantWithRunId` sub-run concurrently — one per invariant, with sub-run identifier `<SkillRunId>-<sub_run_suffix>` and `InvariantPath` as the path to the invariant file. Invoke through the configured skill runner if one is available; otherwise execute by reading `.skills/CheckSingleInvariantWithRunId/SKILL.md` and following its instructions literally. After all sub-runs have completed, read each sub-run receipt `tmp/<SkillRunId>-<sub_run_suffix>.json` and record its `status`, `source`, and `detail`. Each sub-run handles its own cache probe and cache write per `.ai/CACHING.md`: sub-runs reported as `"source": "cache"` were skipped entirely, those with `"source": "regenerated"` were judged in full.

4. **Verdict.** The status is `"pass"` only when `registry.status` is `"pass"` and every sub-run reports `"status": "pass"`. Otherwise `"status": "fail"` when at least one check failed, or `"status": "error"` when this skill could not perform the checks at all (bad parameters or a pre-existing receipt file).

5. **Report.** Tell the user the verdict: that all invariants passed, or every reason they did not — the registry failure detail if any, and each failing invariant with its detail. Also report `cache_summary`: how many invariant checks were served from the cache versus re-run in full.

6. **Write the run receipt** by calling `.skills/CheckAllInvariantsWithRunId/scripts/write-receipt.py` with CLI flags: `--skill-run-id`, `--registry-status pass|fail` (with `--registry-detail TEXT` when the registry fails), and `--sub-run-ids "id1 id2 ..."` listing every `CheckSingleInvariantWithRunId` sub-run identifier separated by spaces. The script reads the sub-run receipts, derives the overall status, computes `cache_summary`, validates the schema, and refuses to overwrite an existing receipt. For an error exit: `--status error --error TEXT` (omit `--registry-status` and `--sub-run-ids`).

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.json` must have exactly these fields:

```json
{
  "skill_run_id": "string — the SkillRunId parameter, verbatim",
  "skill": "CheckAllInvariantsWithRunId",
  "status": "pass | fail | error",
  "registry": {
    "status": "pass | fail",
    "detail": "string|null — set only when the registry check fails"
  },
  "invariants": [
    {
      "invariant": "string — path to the *-INVARIANT.md file, relative to the repository root",
      "sub_run_id": "string — the sub-run identifier passed to CheckSingleInvariantWithRunId",
      "status": "pass | fail | error — as reported by the sub-run receipt",
      "source": "cache | regenerated | null — null when status is 'error'",
      "detail": "string|null — set only when the invariant fails"
    }
  ],
  "cache_summary": {
    "cached": "integer — invariant checks served from the cache",
    "regenerated": "integer — invariant checks re-run in full"
  },
  "error": "string|null — set only when status is 'error' (e.g. missing parameter or a pre-existing receipt file)"
}
```

- `registry` is always present when `status` is not `"error"`;
- `invariants` is `[]` when the registry check fails (no sub-runs were launched) or when the registry lists no invariants; it is `null` when `status` is `"error"`;
- `cache_summary` counts source values across all entries of `invariants`; `cached` counts entries with `"source": "cache"`, `regenerated` counts entries with `"source": "regenerated"`, entries with `"source": null` (status `"error"`) count toward neither; it is `null` when `status` is `"error"`;
- `status` is `"pass"` when `registry.status` is `"pass"` and every entry of `invariants` has `"status": "pass"` (then `error` is `null`);
- `"fail"` when at least one invariant or the registry check is not `"pass"` (then `error` is `null`);
- `"error"` when the checks could not be performed at all (then `registry`, `invariants`, and `cache_summary` are `null`, and `error` explains why).

**Run receipt (final reminder):** before finishing this skill — regardless of outcome, success or error alike — write `tmp/<SkillRunId>.json` containing a single well-formed JSON object conforming to the schema above. The only exception is when `tmp/<SkillRunId>.json` already existed before the run: in that case refuse to run and never overwrite it.
