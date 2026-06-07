---
name: InternalSkillCheckGhRepoAccessWithRunId
description: Checks that the GitHub CLI (`gh`) is installed, authenticated, and can access the repository URL in `.theloop/repo.txt`, and ensures the `theloop` label exists for bugs and pull requests. Use when verifying GitHub access before PR workflows, when `gh` commands fail, or when the user asks to confirm repository connectivity.
argument-hint: <SkillRunId>
---

# InternalSkillCheckGhRepoAccessWithRunId

**Run receipt (write once, never overwrite):** before doing anything else, check whether the file `tmp/<SkillRunId>.json` (relative to the repository root) already exists, where `SkillRunId` is the single parameter of this skill. If it exists, refuse to run: report the error to the user and stop without touching the file. Otherwise, no matter how this skill ends — success, validation failure, or error — you must write `tmp/<SkillRunId>.json` containing exactly one well-formed JSON object following the schema in the "Run receipt schema" section below. Create the `tmp/` directory if it does not exist.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository. The `gh` and `git` commands below reach GitHub over the network but do not touch paths outside this repository.

## Parameters

This skill takes exactly one parameter:

1. `SkillRunId` — a random identifier for this run, supplied by the caller. Used as the run-receipt filename, `tmp/<SkillRunId>.json`. No file by that name may exist prior to the run.

If the parameter is missing, or extra parameters are passed, stop and report an error (and still write the run receipt with `"status": "error"`, provided `tmp/<SkillRunId>.json` did not exist before the run).

## Required configuration

This skill requires `.theloop/repo.txt`: a single-line text file under `.theloop/` containing the GitHub repository URL that this project must access (for example, `https://github.com/owner/repo`). If the file is missing or empty, the skill reports that the target repository is not configured and does not attempt repository access checks.

## Steps

All scripts under `.skills/InternalSkillCheckGhRepoAccessWithRunId/scripts/` are executable and begin with `#!/usr/bin/env python3`; run each one directly by path — never prefix it with `python` or `python3`.

1. **Run the checks.** Run `.skills/InternalSkillCheckGhRepoAccessWithRunId/scripts/check.py` from the repository root. The script prints a JSON object with `repo_url`, a `checks` array, and an `actions` array (side effects such as a label that was created), and exits non-zero when at least one check fails. The checks are:
   - `repo-config` — `.theloop/repo.txt` exists and contains a recognizable GitHub repository URL;
   - `gh-installed` — the `gh` command is available on `PATH`; on failure, the check's `suggestion` tells the user to install the GitHub CLI;
   - `gh-authenticated` — `gh auth status` succeeds; on failure, the check's `suggestion` tells the user to run `gh auth login`;
   - `gh-repo-access` — `gh repo view` succeeds for the configured repository; skipped when earlier checks fail;
   - `gh-label-theloop` — the repository has a `theloop` label (usable on bugs and pull requests); if the label is missing, the script creates it with `gh label create`; skipped when earlier checks fail;
   - `gh-repo-pull` — `git ls-remote` can read `HEAD` from the repository, confirming pull/read access via the configured credentials; skipped when earlier checks fail.

2. **Report.** Tell the user the verdict in plain English:
   - when every check passes or is skipped, GitHub CLI access is ready for the configured repository and the `theloop` label is present;
   - when `.theloop/repo.txt` is missing or invalid, warn clearly that the target repository is not configured for this project and relay the `repo-config` suggestion;
   - when `gh` is not installed, relay the `gh-installed` suggestion;
   - when `gh` is not authenticated, relay the `gh-authenticated` suggestion;
   - when repository access, label, or pull checks fail, relay their `detail` and `suggestion` fields;
   - relay every entry in the script's `actions` array (for example, when the `theloop` label was just created).

3. **Write the run receipt** by calling `.skills/InternalSkillCheckGhRepoAccessWithRunId/scripts/write-receipt.py` with CLI flags: `--skill-run-id` and `--checks-json JSON` (the JSON object printed by `check.py`). For an error exit before the checks run: `--status error --error TEXT`.

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.json` must have exactly these fields:

```json
{
  "skill_run_id": "string — the SkillRunId parameter, verbatim",
  "skill": "InternalSkillCheckGhRepoAccessWithRunId",
  "status": "pass | fail | error",
  "repo_url": "string|null — the URL read from .theloop/repo.txt, or null when unavailable",
  "checks": [
    {
      "check": "repo-config | gh-installed | gh-authenticated | gh-repo-access | gh-label-theloop | gh-repo-pull",
      "status": "pass | fail | skipped",
      "detail": "string|null — set when the check fails or is skipped with context",
      "suggestion": "string|null — set when the check fails with a remediation hint"
    }
  ],
  "error": "string|null — set only when status is 'error' (e.g. missing parameter or a pre-existing receipt file)"
}
```

- `status` is `"pass"` when every check has `"status": "pass"` or `"skipped"`, `"fail"` when at least one check has `"status": "fail"`, and `"error"` when the skill could not run at all;
- `checks` is `[]` when `status` is `"error"`;
- `error` is set only when `status` is `"error"`.

**Run receipt (final reminder):** before finishing this skill — regardless of outcome, success or error alike — write `tmp/<SkillRunId>.json` containing a single well-formed JSON object conforming to the schema above. The only exception is when `tmp/<SkillRunId>.json` already existed before the run: in that case refuse to run and never overwrite it.
