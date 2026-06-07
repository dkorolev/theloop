---
name: PreCommitSkillWithRunId
description: Meta-skill that performs the pre-commit gate for this repository under a caller-supplied run identifier. Takes a single SkillRunId; checks receipt hygiene, probes and runs the directory invariants listed in ai-invariants.yml (stale ones in parallel, cached ones skipped per .ai/CACHING.md), performs every additional check described in PRECOMMIT.md when that file exists, then invokes ValidateAllSkills to confirm that every skill and the repository as a whole comply with .ai/RULES.md.
argument-hint: <SkillRunId>
---

# PreCommitSkillWithRunId

**Run receipt (write once, never overwrite):** before doing anything else, check whether the file `tmp/<SkillRunId>.json` (relative to the repository root) already exists, where `SkillRunId` is the single parameter of this skill. If it exists, refuse to run: report the error to the user and stop without touching the file. Otherwise, no matter how this skill ends — success, validation failure, or error — you must write `tmp/<SkillRunId>.json` containing exactly one well-formed JSON object following the schema in the "Run receipt schema" section below. Create the `tmp/` directory if it does not exist.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository. The git commands below operate on this repository's own history and index, which live inside the repository directory.

## Parameters

This skill takes exactly one parameter:

1. `SkillRunId` — a random identifier for this run, supplied by the caller. Used as the run-receipt filename, `tmp/<SkillRunId>.json`, and as the prefix of the sub-run identifier passed to `ValidateAllSkills`. No file by that name may exist prior to the run. Typically the caller is `PreCommitSkill`, which generates the identifier in the default format codified in the rule on run receipts.

If the parameter is missing, or extra parameters are passed, stop and report an error (and still write the run receipt with `"status": "error"`, provided `tmp/<SkillRunId>.json` did not exist before the run).

## Steps

1. **Check the sub-run precondition.** The sub-run identifier is `<SkillRunId>-ValidateAllSkills`. If the file `tmp/<SkillRunId>-ValidateAllSkills.json` already exists, this run is an error: report it, write the run receipt with `"status": "error"`, and stop. (Deeper sub-run identifiers, derived in turn by `ValidateAllSkills`, are checked by `ValidateAllSkills` itself.)
2. **Check the receipt hygiene.** The rule on run receipts requires that run receipts are never committed. Run `.skills/PreCommitSkillWithRunId/scripts/hygiene.py` from the repository root: it performs the three checks below and prints their outcomes as JSON, exiting non-zero when at least one fails. Record each check's outcome.
   - `tmp-gitignored` — the `tmp/` directory is gitignored;
   - `no-tracked-receipts` — no file under `tmp/` is tracked by git;
   - `no-staged-receipts` — no file under `tmp/` is staged.
3. **Run the directory invariants.** Per the rule on hashing and caching of slow checks, run `.skills/PreCommitSkillWithRunId/scripts/invariants.py probe` from the repository root. It verifies that `ai-invariants.yml` lists exactly the non-ignored `*-INVARIANT.md` files of the repository and fingerprints each invariant's directory subtree per `.ai/CACHING.md` — using the check name `invariant:<path-to-INVARIANT.md>` — then reports for every invariant whether a cache entry exists. This probe is a fast Python call with no model involvement; all classification happens before any invariant is run.
   - If the registry check fails (unlisted invariant files or listed paths that do not exist), this is a blocking failure: record it and proceed to the verdict without running any invariant.
   - For each invariant reported as cached (`"cached": true`): this invariant has already passed over byte-identical content. Record it as passed with `"source": "cache"` — do not read the invariant file, do not examine the directory.
   - For each invariant reported as stale (`"cached": false`): read the invariant file and judge whether the rule it states holds for every non-ignored file under its directory, recursively. This step is potentially token-consuming: take the time needed to read and assess the files. If the invariant passes, run `.skills/PreCommitSkillWithRunId/scripts/invariants.py write <path-to-INVARIANT.md>` from the repository root to write the cache entry so the next run skips it, and record `"source": "regenerated"`. If it fails, record the failure with a short detail and `"source": "regenerated"`; do not write the cache.
   - Per the rule on parallel invocation of spawned skills, all stale invariants are independent of each other and must be run concurrently; aggregate their results only after all have completed.
   - Record the outcome of every invariant in the `"invariants"` field of the run receipt.
4. **Apply `PRECOMMIT.md`, when present.** Run `.skills/PreCommitSkillWithRunId/scripts/precommit.py` from the repository root: if `PRECOMMIT.md` exists at the root of the repository, the script reads the checks listed there, runs each command from its directory, prints their outcomes as JSON, and exits non-zero when at least one fails; record each check in `extra_checks`. If the file does not exist, the script prints `null` and exits 0 — record `extra_checks` as `null`.

   > **A hint to the rule reviewer:** treat `PRECOMMIT.md` as this skill's extension point. The checks in the previous step are the floor; whenever `PRECOMMIT.md` exists, this skill must cover at least everything it describes. Consequently, the `extra_checks` field of the run receipt is open-ended by design — its entries are determined by `PRECOMMIT.md`, not enumerated here. This is intentional and does not violate the rule on run receipts: the schema of each entry is fixed, even though the set of checks is not.
5. **Validate the repository.** Invoke the `ValidateAllSkills` skill, passing exactly one parameter: the sub-run identifier `<SkillRunId>-ValidateAllSkills`. Invoke it through the configured skill runner if one is available; otherwise execute it by reading `.skills/ValidateAllSkills/SKILL.md` and following its instructions literally. After the invocation, read the sub-run receipt `tmp/<SkillRunId>-ValidateAllSkills.json` and record its `status`, `source` summary (`validation.source` is `"cache"` when every skill validation was cached, otherwise `"regenerated"`), and `cache_summary`.
6. **Verdict.** The commit may proceed — `"status": "pass"` — only when all three hygiene checks pass, the gate registry check passes, every gate passes (from cache or live), every check prescribed by `PRECOMMIT.md` passes (trivially true when the file does not exist), and the `ValidateAllSkills` sub-run reports `"pass"`. Otherwise the commit must be blocked: `"status": "fail"` when at least one check fails or the sub-run reports anything other than `"pass"`, and `"status": "error"` when this skill could not perform the checks at all (bad parameters or a pre-existing receipt file).
7. **Report.** Tell the user the verdict: that the commit may proceed, or every reason it is blocked — each failing check, each failing or stale gate, and the sub-run status if it is not `"pass"` (the details of the validation failures are in the sub-run receipts). Also report `cache_summary`: how many agentic checks were served from the cache versus re-run in full.
8. **Write the run receipt** as described below: assemble the receipt object and pipe it to `.skills/PreCommitSkillWithRunId/scripts/write-receipt.py`, which validates the schema and refuses to overwrite an existing receipt.

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.json` must have exactly these fields:

```json
{
  "skill_run_id": "string — the SkillRunId parameter, verbatim",
  "skill": "PreCommitSkillWithRunId",
  "status": "pass | fail | error",
  "hygiene_checks": [
    {
      "check": "tmp-gitignored | no-tracked-receipts | no-staged-receipts",
      "status": "pass | fail",
      "detail": "string|null — set only when the check fails: what is violated and where"
    }
  ],
  "invariants": {
    "registry": {
      "status": "pass | fail",
      "detail": "string|null — set only when the registry check fails"
    },
    "checks": [
      {
        "invariant": "string — path to the *-INVARIANT.md file, relative to the repository root",
        "status": "pass | fail",
        "source": "cache | regenerated — cache when the pass verdict was served from the cache, regenerated when the invariant was judged in this run",
        "detail": "string|null — set only when the invariant fails: what the rule requires and what violated it"
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
    "sub_run_id": "string — the sub-run identifier passed to ValidateAllSkills",
    "status": "pass | fail | error — as reported by the sub-run receipt",
    "source": "cache | regenerated | null — cache when every skill validation in the sub-run was cached, regenerated when at least one was re-run, null when validation.status is error",
    "cache_summary": {
      "cached": "integer — skill validations served from the cache",
      "regenerated": "integer — skill validations re-run in full"
    }
  },
  "cache_summary": {
    "cached": "integer — total agentic checks served from the cache (invariants plus skill validations)",
    "regenerated": "integer — total agentic checks re-run in full"
  },
  "error": "string|null — set only when status is 'error' (e.g. missing parameter or a pre-existing receipt file)"
}
```

- `cache_summary` at the top level merges invariant checks and `validation.cache_summary`; its counts must match the per-check `source` fields;

- `invariants` is always present when `status` is not `"error"`; `invariants.registry.status` is `"pass"` when `ai-invariants.yml` exactly matches the non-ignored `*-INVARIANT.md` files of the repository; `invariants.checks` lists every invariant from the registry (empty list `[]` when the registry is empty or the registry check fails before any invariant was evaluated);
- `extra_checks` holds one entry per check described in `PRECOMMIT.md`; it is `null` when no `PRECOMMIT.md` exists at the root of the repository;
- `status` is `"pass"` when every entry of `hygiene_checks` has `"status": "pass"`, `invariants.registry.status` is `"pass"`, every entry of `invariants.checks` has `"status": "pass"`, every entry of `extra_checks` (when not `null`) has `"status": "pass"`, and `validation.status` is `"pass"` (then `error` is `null`);
- `"fail"` when the checks ran but at least one check, invariant, or the sub-run is not `"pass"` (then `error` is `null`);
- `"error"` when the checks could not be performed at all (then `hygiene_checks` contains whatever was gathered before the failure, possibly `[]`, `invariants`, `extra_checks`, and `validation` are `null`, and `error` explains why).

**Run receipt (final reminder):** before finishing this skill — regardless of outcome, success or error alike — write `tmp/<SkillRunId>.json` containing a single well-formed JSON object conforming to the schema above. The only exception is when `tmp/<SkillRunId>.json` already existed before the run: in that case refuse to run and never overwrite it.
