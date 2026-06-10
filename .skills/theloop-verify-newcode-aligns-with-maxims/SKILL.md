---
name: theloop-verify-newcode-aligns-with-maxims
description: Verifies that the new code — the linear chain of commits the current branch adds on top of the origin's main branch — aligns with the repository's maxims under maxims/. Takes no parameters and generates its own SkillRunId; strictly read-only, it fetches the origin's main, requires the current branch to sit squarely on top of it, judges each new commit's diff and message against every recorded maxim, and reports any violations without creating commits or modifying anything.
---

# theloop-verify-newcode-aligns-with-maxims

This skill verifies that **new code aligns with the repository's maxims**: it takes
the linear chain of commits the current branch adds on top of the origin's main
branch, and judges each commit — its diff *and* its message — against every maxim
recorded under `maxims/` by `theloop-keep-maxims-up-to-date`. All deterministic work
(fetching the origin's main, checking that the branch sits squarely on top of it,
extracting the commit payload, validating the `maxims/` artifact) is done by the
bundled scripts; your only job is the judgment those scripts cannot do — deciding
whether the new code violates a maxim — reported back to the user and recorded in
the run receipt.

Per the rule on run receipts, this is one of the exceptional skills that does not take the `SkillRunId` parameter — it is invoked directly by a human, where a caller-supplied identifier would serve no purpose. It generates a fresh `SkillRunId` of its own and writes its own run receipt.

Running this skill is an operation fully contained within the directory of this
repository: do not read, write, or otherwise access any file outside the repository.
The one outward action is a time-bounded `git fetch` of the origin's main branch,
performed by the bundled script.

**This skill is strictly read-only.** It never creates, amends, or suggests a commit,
never stages anything, and never edits any file of the repository — including the
`maxims/` artifact, which it only reads; the artifact is owned and written exclusively
by `theloop-keep-maxims-up-to-date`. Its only outputs are its report to the user, the
run receipt, and the ephemeral payload file under the gitignored `tmp/`. Fixing a
reported violation is the user's decision and the user's work.

Per the rule on hashing and caching of slow checks, this skill does **not** cache its
judgment: the outcome is determined by the commit range between the origin's main and
`HEAD` — git history and remote state, not a fixed set of working-tree files — and
`.theloop/CACHING.md` requires that such a check must not pretend otherwise.

## Parameters

This skill takes no parameters. If any parameters are passed, stop immediately and
report an error.

## Steps

The Python scripts under `.skills/theloop-verify-newcode-aligns-with-maxims/scripts/`
are executable and begin with `#!/usr/bin/env python3`; run each one directly by
path — never prefix it with `python` or `python3`. Every external `git` call those
scripts make is time-bounded, per the rule on time-bounded operations.

1. **Check the configuration gate, then generate the run identifier.** First run
   `.skills/theloop-verify-newcode-aligns-with-maxims/scripts/check-configured.py`
   from the repository root. If it exits non-zero (the repository has been
   theloopified but `newrepo-theloopify-internal-postinit` has not completed), stop
   immediately: tell the user they must run `newrepo-theloopify-internal-postinit`
   first, and do not generate an identifier. When it reports configured — including
   the not-applicable case in a non-theloopified repository, such as the theloop
   repository itself — continue. Then run
   `.skills/theloop-verify-newcode-aligns-with-maxims/scripts/new-run-id.sh` from the
   repository root: it prints a fresh `SkillRunId` in the default format codified in
   the rule on run receipts, `YYYYMMDD-HHMMSS-{six_random_latin_lowercase_characters}`.
   Tell the user which identifier was generated. Then confirm that
   `tmp/<SkillRunId>.json` does not already exist; if it does, stop immediately and
   report an error without touching the file. **You will write `tmp/<SkillRunId>.json`
   as the run receipt when this skill completes — on success, violations, or error
   alike.**

2. **Validate the maxims artifact.** Run
   `.skills/theloop-verify-newcode-aligns-with-maxims/scripts/read-maxims.py` from
   the repository root. It refuses a missing `maxims/` (there is nothing to verify
   against — tell the user to run `theloop-keep-maxims-up-to-date` first), refuses a
   `maxims/` that lacks the `metadata.json` ownership marker (the path belongs to
   something else), and otherwise prints the per-category `.yml` source-of-truth
   files. On any error, write the run receipt with `"status": "error"` and stop,
   reporting the script's message.

3. **Resolve the new code.** Run
   `.skills/theloop-verify-newcode-aligns-with-maxims/scripts/resolve-newcode.py --run-id <SkillRunId>`
   from the repository root. It fetches the origin's main branch (time-bounded), then
   requires the current branch to sit **squarely on top** of it: the origin's main
   tip must be the merge base of the two, and the range must contain no merge
   commits. On any precondition failure — no `origin` remote, the fetch failed or
   timed out, or the branch is not squarely on top — write the run receipt with
   `"status": "error"` and stop, relaying the script's message verbatim (it tells the
   user to rebase onto the origin's main first). When it reports `commit_count` `0`,
   there is no new code: tell the user so, write the run receipt with
   `"status": "pass"` and zero commits checked, and stop. Otherwise it has written
   the payload — every commit in the range with its full message, stat, and diff, in
   order — to the gitignored `tmp/<SkillRunId>-newcode.txt`.

4. **Judge the new code against the maxims.** This is the only genuine judgment
   step. Read every category `.yml` file reported by step 2, then read the payload
   file from step 3. For each maxim, decide whether any of the new commits violates
   it — judging diffs against code-shaped maxims and commit messages against
   history-shaped ones (commit granularity and message conventions are maxims too).
   Bias toward precision over recall: report a violation only when the evidence in
   the payload is concrete — name the offending commit (short SHA and subject), the
   file when applicable, and the specific maxim violated. A maxim that the new code
   simply does not touch is not a violation.

5. **Report.** Tell the user the verdict: that the new commits align with all
   maxims, or each violation found — the maxim (by its id and category), the
   offending commit and file, and what would bring the code into alignment. Remind
   them this skill changed nothing: acting on the findings is theirs to do.

6. **Write the run receipt** by calling
   `.skills/theloop-verify-newcode-aligns-with-maxims/scripts/write-receipt.py` with
   CLI flags: `--skill-run-id` and `--status pass|fail|error`; when status is `pass`
   or `fail`: `--base SHA`, `--head SHA`, `--commits-checked N`,
   `--categories-checked "a,b"` (comma-separated category ids, empty string for
   none), and — for `fail` — `--violations-json JSON` (the violations array); when
   status is `error`: `--error TEXT`. The script validates the schema and refuses to
   overwrite an existing receipt.

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.json` must have exactly these fields:

```json
{
  "skill_run_id": "string — the generated SkillRunId",
  "skill": "theloop-verify-newcode-aligns-with-maxims",
  "status": "pass | fail | error",
  "base": "string|null — SHA of the origin's main tip the branch sits on, null when error",
  "head": "string|null — SHA of HEAD, null when error",
  "commits_checked": "integer|null — commits judged in the range, null when error",
  "categories_checked": "array of strings|null — maxims category ids judged against, null when error",
  "violations": [
    {
      "maxim": "string — the id of the violated maxim",
      "category": "string — the maxim's category id",
      "evidence": "string — the offending commit (short SHA and subject) and file when applicable",
      "detail": "string — what the maxim requires and how the new code violates it"
    }
  ],
  "error": "string|null — set only when status is error"
}
```

- `status` is `"pass"` when every new commit aligns with every maxim — including the
  case of zero new commits — with `violations` `[]` and `error` `null`;
- `"fail"` when at least one violation was found, listed exhaustively in
  `violations`, with `error` `null`;
- `"error"` when the skill could not perform the verification at all (unexpected
  parameters, a pre-existing receipt, a missing or foreign `maxims/`, no `origin`
  remote, a failed or timed-out fetch, or a branch not squarely on top of the
  origin's main), with the data fields `null`, `violations` `null`, and `error`
  explaining why.

**Run receipt (final reminder):** before finishing this skill — on success,
violations, or error alike — write `tmp/<SkillRunId>.json` containing a single
well-formed JSON object conforming to the schema above, via the `write-receipt.py`
script. The only exception is when the run was aborted because `tmp/<SkillRunId>.json`
already existed before the run: in that case, never overwrite it.
