---
name: CheckAllRulesWithRunId
description: Meta-skill that checks all directory rules listed in ai-rules.yml. Takes a single SkillRunId; verifies the registry, then invokes CheckSingleRuleWithRunId once per rule in parallel (each handles its own caching per .ai/CACHING.md).
argument-hint: <SkillRunId>
invokes: [CheckSingleRuleWithRunId]
---

# CheckAllRulesWithRunId

**Run receipt (write once, never overwrite):** before doing anything else, check whether the file `tmp/<SkillRunId>.json` (relative to the repository root) already exists, where `SkillRunId` is the single parameter of this skill. If it exists, refuse to run: report the error to the user and stop without touching the file. Otherwise, no matter how this skill ends — success, validation failure, or error — you must write `tmp/<SkillRunId>.json` containing exactly one well-formed JSON object following the schema in the "Run receipt schema" section below. Create the `tmp/` directory if it does not exist.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository.

## Parameters

This skill takes exactly one parameter:

1. `SkillRunId` — a random identifier for this run, supplied by the caller. Used as the run-receipt filename, `tmp/<SkillRunId>.json`, and as the prefix of the sub-run identifiers passed to `CheckSingleRuleWithRunId`. No file by that name may exist prior to the run.

If the parameter is missing, or extra parameters are passed, stop and report an error (and still write the run receipt with `"status": "error"`, provided `tmp/<SkillRunId>.json` did not exist before the run).

## Steps

All scripts under `.skills/CheckAllRulesWithRunId/scripts/` are executable and begin with `#!/usr/bin/env python3`; run each one directly by path — never prefix it with `python` or `python3`.

1. **Check the registry and enumerate rules.** Run `.skills/CheckAllRulesWithRunId/scripts/rules.py probe` from the repository root. The script verifies that `ai-rules.yml` lists exactly the non-ignored `*-rule.yml` files of the repository, parses each rule file, fingerprints its resolved scope per `.ai/CACHING.md`, and reports the registry status and the full list of rules — each with its path and the `sub_run_suffix` to use when forming its sub-run identifier.
   - If the registry check fails (unlisted rule files or listed paths that do not exist), this is a blocking failure: record `registry.status = "fail"` with the detail, set `rules = []`, and proceed to the verdict without running any rule.
   - If the registry check passes and no rules are listed, `rules = []` and proceed to the verdict.

2. **Check the sub-run preconditions.** For each rule, the sub-run identifier is `<SkillRunId>-<sub_run_suffix>`, where `sub_run_suffix` is the value provided by the script for that rule. If the file `tmp/<SkillRunId>-<sub_run_suffix>.json` already exists for any rule, this run is an error: report which files are in the way, write the run receipt with `"status": "error"`, and stop before invoking any sub-run.

3. **Check each rule.** Per the rule on parallel invocation of spawned skills, launch every `CheckSingleRuleWithRunId` sub-run concurrently — one per rule, with sub-run identifier `<SkillRunId>-<sub_run_suffix>` and `RulePath` as the path to the rule file. Invoke through the configured skill runner if one is available; otherwise execute by reading `.skills/CheckSingleRuleWithRunId/SKILL.md` and following its instructions literally. After all sub-runs have completed, read each sub-run receipt `tmp/<SkillRunId>-<sub_run_suffix>.json` and record its `status`, `source`, and `detail`. Each sub-run handles its own YAML parsing, cache probe, and cache write per `.ai/CACHING.md`: sub-runs reported as `"source": "cache"` were skipped entirely, those with `"source": "regenerated"` were judged in full.

4. **Verdict.** The status is `"pass"` only when `registry.status` is `"pass"` and every sub-run reports `"status": "pass"`. Otherwise `"status": "fail"` when at least one check failed, or `"status": "error"` when this skill could not perform the checks at all (bad parameters or a pre-existing receipt file).

5. **Report.** Tell the user the verdict: that all rules passed, or every reason they did not — the registry failure detail if any, and each failing rule with its detail. Also report `cache_summary`: how many rule checks were served from the cache versus re-run in full.

6. **Write the run receipt** by calling `.skills/CheckAllRulesWithRunId/scripts/write-receipt.py` with CLI flags: `--skill-run-id`, `--registry-status pass|fail` (with `--registry-detail TEXT` when the registry fails), and `--sub-run-ids "id1 id2 ..."` listing every `CheckSingleRuleWithRunId` sub-run identifier separated by spaces. The script reads the sub-run receipts, derives the overall status, computes `cache_summary`, validates the schema, and refuses to overwrite an existing receipt. For an error exit: `--status error --error TEXT` (omit `--registry-status` and `--sub-run-ids`).

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.json` must have exactly these fields:

```json
{
  "skill_run_id": "string — the SkillRunId parameter, verbatim",
  "skill": "CheckAllRulesWithRunId",
  "status": "pass | fail | error",
  "registry": {
    "status": "pass | fail",
    "detail": "string|null — set only when the registry check fails"
  },
  "rules": [
    {
      "rule": "string — path to the *-rule.yml file, relative to the repository root",
      "sub_run_id": "string — the sub-run identifier passed to CheckSingleRuleWithRunId",
      "status": "pass | fail | error — as reported by the sub-run receipt",
      "source": "cache | regenerated | null — null when status is 'error'",
      "detail": "string|null — set only when the rule fails"
    }
  ],
  "cache_summary": {
    "cached": "integer — rule checks served from the cache",
    "regenerated": "integer — rule checks re-run in full"
  },
  "error": "string|null — set only when status is 'error' (e.g. missing parameter or a pre-existing receipt file)"
}
```

- `registry` is always present when `status` is not `"error"`;
- `rules` is `[]` when the registry check fails (no sub-runs were launched) or when the registry lists no rules; it is `null` when `status` is `"error"`;
- `cache_summary` counts source values across all entries of `rules`; it is `null` when `status` is `"error"`;
- `status` is `"pass"` when `registry.status` is `"pass"` and every entry of `rules` has `"status": "pass"` (then `error` is `null`);
- `"fail"` when at least one rule or the registry check is not `"pass"` (then `error` is `null`);
- `"error"` when the checks could not be performed at all (then `registry`, `rules`, and `cache_summary` are `null`, and `error` explains why).

**Run receipt (final reminder):** before finishing this skill — regardless of outcome, success or error alike — write `tmp/<SkillRunId>.json` containing a single well-formed JSON object conforming to the schema above. The only exception is when `tmp/<SkillRunId>.json` already existed before the run: in that case refuse to run and never overwrite it.
