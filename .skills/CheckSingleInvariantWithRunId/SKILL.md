---
name: CheckSingleInvariantWithRunId
description: Meta-skill that checks a single directory invariant against its subtree. Takes a SkillRunId and an InvariantPath; probes the cache (per .ai/CACHING.md) and skips the check if cached, or reads the invariant rule and judges the subtree if stale; writes the cache entry on a pass.
argument-hint: <SkillRunId> <InvariantPath>
---

# CheckSingleInvariantWithRunId

**Run receipt (write once, never overwrite):** before doing anything else, check whether the file `tmp/<SkillRunId>.json` (relative to the repository root) already exists, where `SkillRunId` is the first parameter of this skill. If it exists, refuse to run: report the error to the user and stop without touching the file. Otherwise, no matter how this skill ends — success, validation failure, or error — you must write `tmp/<SkillRunId>.json` containing exactly one well-formed JSON object following the schema in the "Run receipt schema" section below. Create the `tmp/` directory if it does not exist.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository.

## Parameters

This skill takes exactly two parameters:

1. `SkillRunId` — a random identifier for this run, supplied by the caller. Used as the run-receipt filename, `tmp/<SkillRunId>.json`. No file by that name may exist prior to the run.
2. `InvariantPath` — the path (relative to the repository root) of the `*-INVARIANT.md` file to check, as listed in `ai-invariants.yml`.

If either parameter is missing, or extra parameters are passed, stop and report an error (and still write the run receipt with `"status": "error"`, provided `tmp/<SkillRunId>.json` did not exist before the run).

## Steps

1. **Probe the cache.** Run `.skills/CheckSingleInvariantWithRunId/scripts/invariants.py probe-one <InvariantPath>` from the repository root. The script fingerprints the invariant's directory subtree per `.ai/CACHING.md` under the check name `invariant:<InvariantPath>` and reports whether a cache entry exists for that fingerprint.
   - If the script exits non-zero (e.g. `InvariantPath` is not a non-ignored `*-INVARIANT.md` file), treat this as an error: record the detail, write the run receipt with `"status": "error"`, and stop.
   - If the result reports `"cached": true`: this invariant has already passed over byte-identical content. Record `"status": "pass"` and `"source": "cache"`. Proceed directly to writing the run receipt.
   - If the result reports `"cached": false`: proceed to the next step to judge the invariant.

2. **Judge the invariant.** Read `InvariantPath` to learn the rule it states. Then read every non-ignored file under the directory that contains `InvariantPath`, recursively, and judge whether the rule holds for the directory's current contents. This step may be token-consuming: take the time needed to read and assess the files.
   - If the rule holds: record `"status": "pass"` and `"source": "regenerated"`, then run `.skills/CheckSingleInvariantWithRunId/scripts/invariants.py write <InvariantPath>` from the repository root to write the cache entry so the next run skips this invariant.
   - If the rule does not hold: record `"status": "fail"`, `"source": "regenerated"`, and a short `"detail"` describing what the rule requires and what violated it. Do not write the cache entry.

3. **Write the run receipt** by calling `.skills/CheckSingleInvariantWithRunId/scripts/write-receipt.py` with CLI flags: `--skill-run-id`, `--invariant`, `--status`, and (when status is not `error`) `--source cache|regenerated`; add `--detail TEXT` when status is `fail`; add `--error TEXT` when status is `error`. The script validates the schema and refuses to overwrite an existing receipt.

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.json` must have exactly these fields:

```json
{
  "skill_run_id": "string — the SkillRunId parameter, verbatim",
  "skill": "CheckSingleInvariantWithRunId",
  "invariant": "string — the InvariantPath parameter, verbatim",
  "status": "pass | fail | error",
  "source": "cache | regenerated | null — null only when status is 'error'",
  "detail": "string|null — set only when the invariant fails: what the rule requires and what violated it",
  "error": "string|null — set only when status is 'error' (e.g. missing parameter, pre-existing receipt, or probe failure)"
}
```

- `status` is `"pass"` when the invariant holds (served from cache or after judgment), `"fail"` when it does not hold, and `"error"` when the check could not be performed at all;
- `source` is `"cache"` when the pass verdict was served from the cache, `"regenerated"` when the invariant was judged in this run, and `null` when `status` is `"error"`;
- `detail` is set only when `status` is `"fail"`;
- `error` is set only when `status` is `"error"`.

**Run receipt (final reminder):** before finishing this skill — regardless of outcome, success or error alike — write `tmp/<SkillRunId>.json` containing a single well-formed JSON object conforming to the schema above. The only exception is when `tmp/<SkillRunId>.json` already existed before the run: in that case refuse to run and never overwrite it.
