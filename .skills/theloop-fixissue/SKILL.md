---
name: theloop-fixissue
description: Implements a GitHub issue as a pull request. Takes an issue number, verifies GitHub CLI access, chooses a unique branch name, implements the feature from the issue spec, runs theloop-precommit until it passes, commits, opens a theloop-labeled PR, and journals progress as comments on the issue. Use when the user runs theloop-fixissue with an issue index, wants to implement a filed feature request, or follow up after theloop-makeissue.
argument-hint: <IssueIndex>
invokes: [theloop-internal-check-gh-repo-access, theloop-precommit]
---

# theloop-fixissue

Per the rule on run receipts, this is the exceptional skill that does not take the `SkillRunId` parameter — it is invoked by a human with a GitHub issue number, where a caller-supplied run identifier would serve no purpose. It generates a fresh `SkillRunId` of its own and writes its own run receipt.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository. The `gh` and `git` commands below reach GitHub over the network but operate only on this repository and its configured remote, except that reading your configured git author identity (`git config user.name` and `git config user.email`) may resolve values from your global git configuration.

## Parameters

This skill takes exactly one parameter:

1. `IssueIndex` — the GitHub issue number to implement (a positive integer, as shown in the issue URL or returned by `theloop-makeissue`).

If the parameter is missing, if extra parameters are passed, or if `IssueIndex` is not a positive integer, stop immediately and report an error.

## Journal

Throughout this run, record progress on the GitHub issue by posting comments via `.skills/theloop-fixissue/scripts/issue-comment.py`. Each comment is prefixed automatically with **`theloop journal`** so the timeline stays readable. Post a journal entry at every milestone below — do not skip steps:

| When | Comment text (adapt placeholders) |
|------|-----------------------------------|
| After choosing a branch | `started working; chose branch \`<branch>\`` |
| After committing | `committed <sha>` for a single commit, or `committed <sha1>, <sha2>, …` listing every new commit on this branch (short SHAs, seven characters each) |
| After pushing to the remote | `pushed <sha>`, or `pushed <sha1>, <sha2>, …` listing every commit pushed (the same short SHAs as the commit entry) |
| Before each theloop-precommit run | `running the checks` |
| When a theloop-precommit run fails | `checks failed — <failing check(s)>` — record the failure itself, naming each failing check, before you begin fixing |
| During the fix loop | `fixing …` — name the failing check or error in the same comment |
| After the PR is created | `created PR #<pr_number>` |
| While waiting on GitHub gates | `waiting on GitHub checks: <check names>` |
| After the GitHub gates settle | `GitHub checks passed`, or `GitHub checks failed — <failing check(s)>` |
| When the bounded wait on GitHub gates times out | `GitHub checks timed out — <still-pending check(s)>` |
| When restarting a flaky gate | `restarting flaky gate <name>` |
| When fixing a red gate | `fixing GitHub gate <name> — <root cause>` |

Use `--body-file` when the comment is long; otherwise `--body TEXT`.

When referring to a GitHub issue or pull request number in journal text, PR bodies, or commit messages, always write **`Issue #N`** or **`PR #N`** (capitalized prefix, hash, number) — never bare `#N` alone, and never a Markdown link whose anchor text is `#N`. GitHub autolinks `#N`; duplicating it as `[#N](url)` produces doubled links like `#2 — #2`. Link each issue or PR at most once: rely on autolinking for `Issue #N` / `PR #N`, or use a single descriptive link such as `[Issue #N: title](url)` — not both. The sole exception is the PR closing line: keep plain `Closes #N` with no Markdown link so merging auto-closes the issue.

## Sub-skill execution

Do **not** invoke sub-skills via the Skill tool runner. Execute each sub-skill **inline** by reading its `.skills/<SkillName>/SKILL.md` and following it directly. The Skill tool presents its result as a conversational endpoint; inline execution keeps control in this skill. **Never treat a sub-skill completion as the end of this run** — always continue to the next step unless this skill explicitly says to stop.

## Steps

The Python scripts under `.skills/theloop-fixissue/scripts/` are executable and begin with `#!/usr/bin/env python3`; run each one directly by path — never prefix it with `python` or `python3`.

1. **Check the configuration gate and git identity, then generate the run identifier.** First run `.skills/theloop-fixissue/scripts/check-configured.py` from the repository root. If it exits non-zero (the repository has been theloopified but `newrepo-theloopify-internal-postinit` has not completed), stop immediately: tell the user they must run `newrepo-theloopify-internal-postinit` before implementing an issue, and do not generate an identifier. When it reports configured — including the not-applicable case in a non-theloopified repository, such as the theloop repository itself — continue. Next, confirm a git author identity is configured: run `git config user.name` and `git config user.email`. If either prints nothing (unset or empty), stop immediately — tell the user to set their git identity first (for example, `git config --global user.name "Your Name"` and `git config --global user.email "you@example.com"`) before re-running this skill, since the commit and push performed later in this skill would otherwise fail or be misattributed — and do not generate an identifier. When both are set, continue. Then run `.skills/theloop-fixissue/scripts/new-run-id.sh` from the repository root: it prints a fresh `SkillRunId` in the default format codified in the rule on run receipts, `YYYYMMDD-HHMMSS-{six_random_latin_lowercase_characters}` — the local date and time at which the run started, followed by six random lowercase Latin letters (for example, `20260607-153012-kqzwxy`). Tell the user which identifier was generated. Then confirm that `tmp/<SkillRunId>.json` does not already exist; if it does, stop immediately and report an error without touching the file.

2. **Verify GitHub access.** Execute `theloop-internal-check-gh-repo-access` **inline** (see Sub-skill execution above): read `.skills/theloop-internal-check-gh-repo-access/SKILL.md` and follow it directly with exactly one parameter — the sub-run identifier `<SkillRunId>-theloop-internal-check-gh-repo-access`. Read the sub-run receipt at `tmp/<SkillRunId>-theloop-internal-check-gh-repo-access.json`. If its `status` is not `"pass"`, relay every failing check and its remediation suggestion to the user, write the run receipt with `"status": "fail"`, and stop.
   - When the check **passes**, immediately tell the user `GitHub access confirmed — loading Issue #<IssueIndex>` and **continue to step 3 without pausing**. Do not end the run here.

3. **Load the issue.** Run `.skills/theloop-fixissue/scripts/fetch-issue.py --issue-number <IssueIndex>` from the repository root. The script prints a JSON object with `number`, `title`, `body`, `url`, and `labels`. If the issue does not exist or cannot be read, write the run receipt with `"status": "error"` and stop. Treat the issue `body` as the authoritative feature specification (the same Markdown structure written by `theloop-makeissue`). Warn the user if the `theloop` label is missing, but continue unless the issue body is empty.

4. **Claim the issue.** Run `.skills/theloop-fixissue/scripts/claim-issue-work.py --issue-number <IssueIndex>` from the repository root. This must be the **first** action on the issue in this run — before choosing a branch or posting any journal comment. The script posts `Taken into work by **theloop-fixissue**.`, then immediately scans **other** issue comments for an existing "taken into work" claim (retracted comments — those containing `Nevermind; already in the works.` — do not count). If another claim exists, the script **edits** the comment it just posted: strike out the claim and append `Nevermind; already in the works.` Read the JSON output:
   - When `"retracted": true`, tell the user the issue is already being worked on, write the run receipt with `"status": "fail"`, and **stop** — do not branch, implement, or open a PR.
   - When `"claimed": true`, continue.

5. **Prepare the branch.** From the repository root, update the default branch: `git fetch origin` and check out a clean, up-to-date base (typically `main` or `master` — use whichever exists and tracks `origin`). Derive a short, memorable branch name from the issue title: lowercase, words separated by hyphens, no special characters, at most 40 characters (for example, `add-issue-pr-skill` for "Add theloop-fixissue skill"). If the first candidate is taken, append `-2`, `-3`, and so on until free. Run `.skills/theloop-fixissue/scripts/check-branch.py --branch <candidate>` for each candidate; the script exits 0 when the branch is available both locally and on the remote, and prints JSON with `"available": true`. When a name is free, run `git checkout -b <branch>`. Journal: post `started working; chose branch \`<branch>\`` via `issue-comment.py`.

6. **Write the feature design document.** Writing a design document before the code is a deliberate, encouraged practice — do not skip it. Create a Markdown design document with a **feature-specific filename** derived from the issue title (for example, `issue-pr-skill.md` or `dark-mode-toggle.md`) — never a generic name such as `FEATURE.md` or `DESIGN-DOC.md`. Place it following the repository's existing convention for design documents: in a dedicated design-docs directory if one exists (such as `design-docs/`, `docs/design/`, or `docs/`), or alongside the code the feature touches when that is the established pattern. If the repository has no such convention, create a top-level `design-docs/` directory and put the document there. Base it on the issue body. The document must contain:
   - A title and one-paragraph summary
   - The rationale for the design
   - An implementation outline: key components, responsibilities, and interactions
   - A "how to rebuild" section so the feature can be reconstructed from the document alone

   Record the chosen path for the run receipt.

7. **Implement the feature.** Using the issue body and the design document as the specification, write or modify the source files needed to realize the feature. Keep code, configuration, and tests consistent with the design document.

8. **Run theloop-precommit.** Journal: `running the checks`. Execute `theloop-precommit` **inline** (see Sub-skill execution above): read `.skills/theloop-precommit/SKILL.md` and follow it directly, passing no parameters. Record the `SkillRunId` that `theloop-precommit` generates and whether its final verdict was `"pass"`. When it finishes, continue to step 9 — do not treat theloop-precommit completion as the end of this run.

9. **Evaluate the outcome.**
   - If `theloop-precommit` reported `"pass"`, proceed to step 11.
   - If it reported `"fail"` or `"error"`, journal `checks failed — <failing check(s)>` (naming each failing check from the receipt) so the local gate failure is timestamped in the issue, then proceed to the fix loop (step 10).

10. **Fix loop.** While `theloop-precommit` has not reported `"pass"`, and fewer than five total `theloop-precommit` invocations have occurred in this run:
   a. Journal: `fixing …` — summarize what failed.
   b. Read every failing check from the most recent `theloop-precommit` receipt and its sub-run receipts.
   c. Fix the root cause; align implementation with the design document, updating the document first when it must change.
   d. Do not remove or weaken a check to make it pass.
   e. Journal: `running the checks`, then invoke `theloop-precommit` again (step 8) and re-evaluate (step 9).

   If `theloop-precommit` has still not reported `"pass"` after five total invocations, write the run receipt with `"status": "fail"` and stop.

11. **Commit and push.** Stage the changes by running `.skills/theloop-fixissue/scripts/stage-allowed.py` from the repository root: it stages every change except the paths listed in `.theloop/do_not_commit.txt`, so theloop instrumentation (the `.theloop/` scaffolding, the agent skill symlinks, `tmp/`, and the `.gitignore` change `theloopify` made) is hard-excluded and can never land in a commit. In the theloop repository itself there is no `.theloop/do_not_commit.txt`, so it stages everything, as before. Feature design documents are user artifacts and are not excluded.

   **Commit the work the way its reviewer will want to read it.** Picture the person who will review this pull request. Even though you produced the change all at once, break it into commits so that logically disjoint changes land in separate commits — for example, the design document, each independent component, and the tests can each be their own commit. Keep every commit local and self-contained, under ~400 lines of diff where possible. Give every commit a short, crisp subject line and a detailed body that explains what changed and why. A genuinely atomic change is fine as a single commit — do not split what belongs together, and do not bundle what does not.

   To produce more than one commit while preserving the exclusions above, run `stage-allowed.py` once and read its `staged` list (the paths cleared to commit) and its `excluded` prefixes. Then, for each logical group: clear the index with `git restore --staged .`, stage just that group with `git add -- <paths>` — choosing only paths from the `staged` list and never one under an `excluded` prefix — and commit. After the final group, run `stage-allowed.py` again and confirm its `staged` list is now empty, so no allowed change was left uncommitted. When a single commit is appropriate, run `stage-allowed.py` and commit directly.

   Reference the issue in every commit message (for example, `Implement feature for Issue #<IssueIndex>`), and journal every new commit SHA on the branch. Every commit must be authored by the user's configured git identity — never by the AI assistant: do not add any AI-assistant attribution to the commit message (no `Generated with …` line, no `Co-Authored-By:` trailer naming an AI assistant, model, or tool, and no other mention of the AI that produced the change). Run `git push -u origin <branch>`, then journal `pushed <sha…>` listing the same short SHAs you committed, so the push is timestamped in the issue.

12. **Create the pull request.** Build a PR body and save it to `tmp/<SkillRunId>-pr-body.md`. The body **must** include all of the following:
   - A prominent notice that **this pull request was created by theloop** (for example, a blockquote near the top: `> This pull request was created by **theloop**.`).
   - A statement that **this PR implements Issue #\<IssueIndex\>** (substitute the issue number), with the issue title linked once to the issue URL from step 3 (see GitHub reference formatting under Journal).
   - A pointer that the **problem statement, acceptance criteria, and design decisions** are recorded in that issue — reviewers should read the issue for full context rather than duplicating the entire spec in the PR.
   - Plain `Closes #<IssueIndex>.` on its own line (no Markdown link) so merging auto-closes the issue. Keep the keyword immediately before `#<IssueIndex>` — do not insert any word such as "issue" between them, or GitHub will not auto-close (a trailing period after the number is fine).
   - A brief summary of what was implemented in this PR.
   - The path to the feature design document written in step 6.

   Use this structure (adapt placeholders; keep the theloop notice and issue pointer):

   ```markdown
   > This pull request was created by **theloop**.

   This PR implements Issue #<IssueIndex> — [<issue title>](<issue_url>).

   The problem statement, acceptance criteria, and design decisions are recorded in that issue; read it for full context.

   Closes #<IssueIndex>.

   ## Summary
   One or two paragraphs on what this PR changes.

   ## Design document
   `<feature_doc_path>`
   ```

   Run `.skills/theloop-fixissue/scripts/create-pr.py` with `--title TITLE` (the issue title, or a concise variant), `--body-file tmp/<SkillRunId>-pr-body.md`, and `--head <branch>`. The script creates a PR with the `theloop` label and prints JSON with `pr_number` and `pr_url`. Journal: `created PR #<pr_number>`.

13. **Drive the GitHub gates to green.** After the PR is opened, the repository may run required GitHub checks (CI and other status gates) against it. If the PR has any such gates, **this skill is not done until every one of them is green.** Journal around the wait so the issue timeline records it with timestamps:
    - Before waiting, journal `waiting on GitHub checks: <check names>` — list the pending checks; if you cannot enumerate them, write `waiting on GitHub checks`.
    - Poll the gates roughly every ten seconds until every one has settled — green (passed) or red (failed) — rather than leaving while any is still pending. Per the rule on time-bounded operations, never let this wait run unbounded: run `timeout 1800 gh pr checks <pr_number> --watch --interval 10` from the repository root — the watch blocks until the gates settle and exits non-zero if any gate is red, while the 30-minute `timeout` bound guarantees a slow or stuck gate cannot stall the run indefinitely. The bound applies per wait: restarting a flaky gate or pushing a fix starts a fresh bounded wait.
    - When the bound elapses with gates still unsettled (`timeout` kills the watch with exit code 124), treat it as a timeout error, never a reason to keep waiting: journal `GitHub checks timed out — <still-pending check(s)>`, report the timeout and the still-pending gates to the user, write the run receipt with `"status": "fail"`, and stop.
    - If the PR has no required GitHub checks (`gh pr checks` reports none), journal `no GitHub checks configured` and continue to the final report.
    - When every gate is green, journal `GitHub checks passed` and continue to the final report.
    - When one or more gates are red, journal `GitHub checks failed — <failing check(s)>`, then resolve each failing gate and go back to polling. Repeat as many times as necessary until every gate is green:
        - **Likely flakiness** — when the failure is plainly infrastructural and transient rather than caused by this change (for example, a Docker image or dependency that could not be downloaded, a runner that died mid-job, a network timeout): just restart the gate — `gh run rerun <run-id> --failed` (read the run id from `gh pr checks` or `gh run list`). Journal `restarting flaky gate <name>`.
        - **A real failure** — otherwise, read the gate's logs (`gh run view <run-id> --log-failed`) and dig down to the root cause. Fix it diligently: work out the goal the gate is enforcing and make the code actually meet that goal. Do **not** remove, disable, or weaken the gate, and do **not** paper over it with a hack. Journal `fixing GitHub gate <name> — <root cause>`, apply the fix, then commit and push it under step 11's commit-and-push discipline (journal `committed <sha…>` and `pushed <sha…>`); the push re-triggers the gates.
        - After restarting a gate or pushing a fix, journal `waiting on GitHub checks` again and poll as above.
    - Only when every gate is green is the GitHub work done. Stop with failure only as a genuine last resort: if a gate stays red because the change really does not meet the gate's goal and the sole way to make it pass would be to weaken or remove the gate, do not do that — journal the situation, write the run receipt with `"status": "fail"`, report it to the user, and stop. Never declare success while a gate is red.

14. **Final report.** Tell the user:
    - That the pull request was created successfully
    - The PR number and full PR URL — prominently, on their own lines
    - The branch name and issue URL
    - The outcome of the GitHub gates (passed, failed with which checks, or none configured)
    - The path of the feature design document
    - The `SkillRunId` of this run and the `SkillRunId` of the final `theloop-precommit` run
    - A brief summary of what was implemented

15. **Write the run receipt** by calling `.skills/theloop-fixissue/scripts/write-receipt.py` with CLI flags: `--skill-run-id`, `--status pass|fail|error`; when status is `pass`: `--issue-number N`, `--issue-url URL`, `--branch NAME`, `--pr-number N`, `--pr-url URL`, `--feature-doc-path PATH`, `--implementation-attempts N`, `--pre-commit-skill-run-id ID`, `--gh-check-sub-run-id ID`, and `--commits "sha1 sha2 ..."` (space-separated short SHAs of commits on this branch not on the base); when status is `fail`: include whatever fields were determined before failure; when status is `error`: `--error TEXT`. The script validates the schema and refuses to overwrite an existing receipt.

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.json` must have exactly these fields:

```json
{
  "skill_run_id": "string — the generated SkillRunId",
  "skill": "theloop-fixissue",
  "status": "pass | fail | error",
  "issue_number": "integer|null — the IssueIndex parameter, null when status is error before the issue was loaded",
  "issue_url": "string|null — the GitHub issue URL, null when unavailable",
  "branch_name": "string|null — the branch used for implementation, null when not created",
  "pr_number": "integer|null — the GitHub pull request number, null when no PR was created",
  "pr_url": "string|null — the full GitHub pull request URL, null when no PR was created",
  "feature_doc_path": "string|null — path to the design document, null when status is error",
  "implementation_attempts": "integer|null — total theloop-precommit invocations, null when status is error",
  "pre_commit_skill_run_id": "string|null — SkillRunId of the final theloop-precommit run, null when status is error",
  "gh_check_sub_run_id": "string|null — theloop-internal-check-gh-repo-access sub-run identifier, null when status is error before that sub-run",
  "commits": ["string — short commit SHA, seven characters"] ,
  "error": "string|null — set only when status is error"
}
```

- `commits` is `[]` when no commits were made, and `null` only when `status` is `"error"` before any commit;
- `status` is `"pass"` when the PR was created, the final `theloop-precommit` run reported `"pass"`, and every GitHub gate on the PR is green — or the PR has no GitHub gates (then `error` is `null`);
- `"fail"` when checks or PR creation failed after partial progress, a GitHub gate stayed red and could not be driven green without weakening it, or the bounded wait on the GitHub gates timed out (then `error` is `null`);
- `"error"` when the skill could not proceed — bad parameters, missing issue, or a pre-existing receipt file (then nullable fields are `null` and `error` explains why).

**Run receipt (final reminder):** before finishing this skill — regardless of outcome, success, failure, or error alike — write `tmp/<SkillRunId>.json` containing a single well-formed JSON object conforming to the schema above. The only exception is when `tmp/<SkillRunId>.json` already existed before the run: in that case, never overwrite it.
