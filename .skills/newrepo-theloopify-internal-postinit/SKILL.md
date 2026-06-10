---
name: newrepo-theloopify-internal-postinit
description: One-time agentic setup that finishes instrumenting a theloop client repository after theloopify. Analyzes the repository's documentation, test and lint tooling, and CI gates, then authors a free-form PRECOMMIT.md and flips the configuration gate so the other workflow skills may run. Takes no parameters; generates its own SkillRunId and writes its own run receipt.
---

# newrepo-theloopify-internal-postinit

Per the rule on run receipts, this is the exceptional skill that does not take the `SkillRunId` parameter — it is invoked by a human once, immediately after `theloopify`, where a caller-supplied run identifier would serve no purpose. It generates a fresh `SkillRunId` of its own and writes its own run receipt.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository. The commands below operate only on this repository's own working tree.

## Parameters

This skill takes no parameters. If any parameters are passed, stop immediately and report an error.

## Steps

The scripts under `.skills/newrepo-theloopify-internal-postinit/scripts/` are executable; run each one directly by path — never prefix it with `python`, `python3`, or `sh`.

1. **Generate the run identifier.** Run `.skills/newrepo-theloopify-internal-postinit/scripts/new-run-id.sh` from the repository root: it prints a fresh `SkillRunId` in the default format codified in the rule on run receipts, `YYYYMMDD-HHMMSS-{six_random_latin_lowercase_characters}` — the local date and time at which the run started, followed by six random lowercase Latin letters (for example, `20260607-153012-kqzwxy`). Tell the user which identifier was generated. Then confirm that `tmp/<SkillRunId>.json` does not already exist; if it does, stop immediately and report an error without touching the file.

2. **Check the preconditions.** Run `.skills/newrepo-theloopify-internal-postinit/scripts/configure-preconditions.py` from the repository root. It reports whether this skill is allowed to run:
   - refused with reason `already-configured` when `.theloop/configure_the_loop.done` exists — configuration runs at most once per clone;
   - refused with reason `not-theloopified` when `.theloop/theloopified` is absent — the repository must be instrumented with `theloopify` first;
   - refused with reason `not-pending` when `.theloop/must_run_configure_the_loop.txt` is absent.

   If it exits non-zero (refused), relay the reason and detail to the user, write the run receipt with `"status": "fail"`, and stop. When it reports `"allowed": true`, continue.

3. **Analyze the repository.** Read enough of the repository to author correct pre-commit checks, conservatively. Look at:
   - documentation — `README`, `CONTRIBUTING`, and anything under `docs/`;
   - test and lint tooling — `package.json` scripts, `pyproject.toml`, `Makefile` targets, `Cargo.toml`, and similar;
   - CI and GitHub gates — `.github/workflows/` and, where it helps, required checks visible via `gh`;
   - an existing repo-root `PRECOMMIT.md`, if present — review it and extend it; never blindly overwrite checks already recorded there.

4. **Write `PRECOMMIT.md`.** Author (or extend) a repo-root `PRECOMMIT.md` as a plain, free-form Markdown file — not YAML. Structure it however reads clearly: a bulleted or numbered list, or sections such as `## Tests` and `## Lint`. Each entry must name the check, say where to run it (directory or scope), and give the exact command or steps to run — in human-readable prose. Add only checks that are clearly correct, preferring the repository's own documented commands over guesses. Record the path (`PRECOMMIT.md`) and the names of the checks you wrote for the run receipt.

5. **Verify (recommended).** Encourage the user to run `theloop-precommit` next to confirm the generated checks pass, and revise `PRECOMMIT.md` if they do not. This skill does not run `theloop-precommit` itself; verification is a separate step the user triggers.

6. **Flip the configuration gate.** Run `.skills/newrepo-theloopify-internal-postinit/scripts/mark-configured.py` from the repository root (optionally with `--summary "one line"`). It writes `.theloop/configure_the_loop.done` and removes `.theloop/must_run_configure_the_loop.txt`, so the other workflow skills become available. If this step fails — for any reason — leave the repository unconfigured: do not retry by hand, report the failure, write the run receipt with `"status": "fail"`, and stop so the user can rerun this skill.

7. **Final report.** Tell the user:
   - That configuration is complete and the workflow skills (`theloop-makeissue`, `theloop-fixissue`, `theloop-buildthis`, `theloop-precommit`) are now available;
   - The path of the `PRECOMMIT.md` written and the checks it now contains;
   - The `SkillRunId` of this run.

8. **Write the run receipt** by calling `.skills/newrepo-theloopify-internal-postinit/scripts/write-receipt.py` with CLI flags: `--skill-run-id`, `--status pass|fail|error`; when status is `pass`: `--precommit-md-path PATH` and `--checks-configured "name1 name2 ..."`; when status is `fail`: optionally `--precommit-md-path PATH` if a draft was written before the failure; when status is `error`: `--error TEXT`. The script validates the schema and refuses to overwrite an existing receipt.

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.json` must have exactly these fields:

```json
{
  "skill_run_id": "string — the generated SkillRunId",
  "skill": "newrepo-theloopify-internal-postinit",
  "status": "pass | fail | error",
  "precommit_md_path": "string|null — path to the PRECOMMIT.md written, null when none was written",
  "checks_configured": ["string — a short name of a check written into PRECOMMIT.md"],
  "error": "string|null — set only when status is error"
}
```

- `status` is `"pass"` when `PRECOMMIT.md` was written and the configuration gate was flipped (then `precommit_md_path` is set, `checks_configured` is the list of checks written, and `error` is `null`);
- `"fail"` when the preconditions refused the run or configuration could not be completed (then `checks_configured` is `null` and `error` is `null`);
- `"error"` when the skill could not proceed at all — unexpected parameters or a pre-existing receipt file (then `precommit_md_path` and `checks_configured` are `null`, and `error` explains why).

**Run receipt (final reminder):** before finishing this skill — regardless of outcome, success, failure, or error alike — write `tmp/<SkillRunId>.json` containing a single well-formed JSON object conforming to the schema above. The only exception is when `tmp/<SkillRunId>.json` already existed before the run: in that case, never overwrite it.
