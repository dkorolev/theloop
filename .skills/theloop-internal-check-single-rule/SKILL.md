---
name: theloop-internal-check-single-rule
description: Meta-skill that checks a single directory rule against its scoped files. Takes a SkillRunId and a RulePath; parses the YAML rule file, probes the cache (per .theloop/CACHING.md), skips if cached, or judges the scoped files if stale; writes the cache entry on a pass.
argument-hint: <SkillRunId> <RulePath>
---

# theloop-internal-check-single-rule

**Run receipt (write once, never overwrite):** before doing anything else, check whether the file `tmp/<SkillRunId>.json` (relative to the repository root) already exists, where `SkillRunId` is the first parameter of this skill. If it exists, refuse to run: report the error to the user and stop without touching the file. Otherwise, no matter how this skill ends — success, validation failure, or error — you must write `tmp/<SkillRunId>.json` containing exactly one well-formed JSON object following the schema in the "Run receipt schema" section below. Create the `tmp/` directory if it does not exist.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository.

## Parameters

This skill takes exactly two parameters:

1. `SkillRunId` — a random identifier for this run, supplied by the caller. Used as the run-receipt filename, `tmp/<SkillRunId>.json`. No file by that name may exist prior to the run.
2. `RulePath` — the path (relative to the repository root) of the `*-rule.yml` file to check, as listed in `ai-rules.yml`.

If either parameter is missing, or extra parameters are passed, stop and report an error (and still write the run receipt with `"status": "error"`, provided `tmp/<SkillRunId>.json` did not exist before the run).

## Steps

All scripts under `.skills/theloop-internal-check-single-rule/scripts/` are executable and begin with `#!/usr/bin/env python3`; run each one directly by path — never prefix it with `python` or `python3`.

1. **Parse and probe the cache.** Run `.skills/theloop-internal-check-single-rule/scripts/rules.py probe-one <RulePath>` from the repository root. The script validates the YAML syntax and schema, resolves the scoped file set per `.theloop/RULE-FILES.md`, fingerprints that scope per `.theloop/CACHING.md` under the check name `rule:<RulePath>`, and reports whether a cache entry exists.
   - If the script exits with code 2 (e.g. `RulePath` is not a non-ignored `*-rule.yml` file), treat this as an error: record the detail, write the run receipt with `"status": "error"`, and stop.
   - If the result reports `"parse_status": "fail"`: the rule file is invalid. Record `"status": "fail"`, `"source": "regenerated"`, and `"detail"` from the script output. Proceed to writing the run receipt without judging or caching.
   - If the result reports `"cached": true`: this rule has already passed over byte-identical scoped content. Record `"status": "pass"` and `"source": "cache"`. Proceed directly to writing the run receipt.
   - If the result reports `"cached": false` and `"parse_status": "pass"`: proceed to the next step to judge the rule.

2. **Judge the rule.** Run `.skills/theloop-internal-check-single-rule/scripts/rules.py parse <RulePath>` to obtain the `rule_text` and `scope_files` list. Read only the files listed in `scope_files` (which always includes the rule file itself). Judge whether the `rule_text` holds for those files. Do not read any file outside `scope_files`. This step may be token-consuming: take the time needed to read and assess the scoped files.
   - If the rule holds: record `"status": "pass"` and `"source": "regenerated"`, then run `.skills/theloop-internal-check-single-rule/scripts/rules.py write <RulePath>` from the repository root to write the cache entry so the next run skips this rule.
   - If the rule does not hold: record `"status": "fail"`, `"source": "regenerated"`, and a short `"detail"` describing what the rule requires and what violated it. Do not write the cache entry.

3. **Write the run receipt** by calling `.skills/theloop-internal-check-single-rule/scripts/write-receipt.py` with CLI flags: `--skill-run-id`, `--rule`, `--status`, and (when status is not `error`) `--source cache|regenerated`; add `--detail TEXT` when status is `fail`; add `--error TEXT` when status is `error`. The script validates the schema and refuses to overwrite an existing receipt.

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.json` must have exactly these fields:

```json
{
  "skill_run_id": "string — the SkillRunId parameter, verbatim",
  "skill": "theloop-internal-check-single-rule",
  "rule": "string — the RulePath parameter, verbatim",
  "status": "pass | fail | error",
  "source": "cache | regenerated | null — null only when status is 'error'",
  "detail": "string|null — set only when the rule fails: what the rule requires and what violated it",
  "error": "string|null — set only when status is 'error' (e.g. missing parameter, pre-existing receipt, or probe failure)"
}
```

- `status` is `"pass"` when the rule holds (served from cache or after judgment), `"fail"` when it does not hold or the YAML is invalid, and `"error"` when the check could not be performed at all;
- `source` is `"cache"` when the pass verdict was served from the cache, `"regenerated"` when the rule was parsed and judged in this run, and `null` when `status` is `"error"`;
- `detail` is set only when `status` is `"fail"`;
- `error` is set only when `status` is `"error"`.

**Run receipt (final reminder):** before finishing this skill — regardless of outcome, success or error alike — write `tmp/<SkillRunId>.json` containing a single well-formed JSON object conforming to the schema above. The only exception is when `tmp/<SkillRunId>.json` already existed before the run: in that case refuse to run and never overwrite it.
