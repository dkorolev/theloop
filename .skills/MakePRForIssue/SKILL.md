---
name: MakePRForIssue
description: Implements a GitHub issue as a pull request. Takes an issue number, verifies GitHub CLI access, chooses a unique branch name, implements the feature from the issue spec, runs PreCommitSkill until it passes, commits, opens a theloop-labeled PR, and journals progress as comments on the issue. Use when the user runs MakePRForIssue with an issue index, wants to implement a filed feature request, or follow up after IssueWhatWeJustDiscussed.
argument-hint: <IssueIndex>
invokes: [InternalSkillCheckGhRepoAccessWithRunId, PreCommitSkill]
---

# MakePRForIssue

Per the rule on run receipts, this is the exceptional skill that does not take the `SkillRunId` parameter — it is invoked by a human with a GitHub issue number, where a caller-supplied run identifier would serve no purpose. It generates a fresh `SkillRunId` of its own and writes its own run receipt.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository. The `gh` and `git` commands below reach GitHub over the network but operate only on this repository and its configured remote.

## Parameters

This skill takes exactly one parameter:

1. `IssueIndex` — the GitHub issue number to implement (a positive integer, as shown in the issue URL or returned by `IssueWhatWeJustDiscussed`).

If the parameter is missing, if extra parameters are passed, or if `IssueIndex` is not a positive integer, stop immediately and report an error.

## Journal

Throughout this run, record progress on the GitHub issue by posting comments via `.skills/MakePRForIssue/scripts/issue-comment.py`. Each comment is prefixed automatically with **`theloop journal`** so the timeline stays readable. Post a journal entry at every milestone below — do not skip steps:

| When | Comment text (adapt placeholders) |
|------|-----------------------------------|
| After choosing a branch | `started working; chose branch \`<branch>\`` |
| After committing | `committed <sha>` for a single commit, or `committed <sha1>, <sha2>, …` listing every new commit on this branch (short SHAs, seven characters each) |
| Before each PreCommitSkill run | `running the checks` |
| During the fix loop | `fixing …` — name the failing check or error in the same comment |
| After the PR is created | `created PR #<pr_number> — <pr_url>` |

Use `--body-file` when the comment is long; otherwise `--body TEXT`.

## Steps

The Python scripts under `.skills/MakePRForIssue/scripts/` are executable and begin with `#!/usr/bin/env python3`; run each one directly by path — never prefix it with `python` or `python3`.

1. **Generate the run identifier.** Run `.skills/MakePRForIssue/scripts/new-run-id.sh` from the repository root: it prints a fresh `SkillRunId` in the default format codified in the rule on run receipts, `YYYYMMDD-HHMMSS-{six_random_latin_lowercase_characters}` — the local date and time at which the run started, followed by six random lowercase Latin letters (for example, `20260607-153012-kqzwxy`). Tell the user which identifier was generated. Then confirm that `tmp/<SkillRunId>.json` does not already exist; if it does, stop immediately and report an error without touching the file.

2. **Verify GitHub access.** Invoke the `InternalSkillCheckGhRepoAccessWithRunId` skill with exactly one parameter: the sub-run identifier `<SkillRunId>-InternalSkillCheckGhRepoAccessWithRunId`. Invoke it through the configured skill runner if one is available; otherwise execute it by reading `.skills/InternalSkillCheckGhRepoAccessWithRunId/SKILL.md` and following its instructions literally. Read the sub-run receipt at `tmp/<SkillRunId>-InternalSkillCheckGhRepoAccessWithRunId.json`. If its `status` is not `"pass"`, relay every failing check and its remediation suggestion to the user, write the run receipt with `"status": "fail"`, and stop.

3. **Load the issue.** Run `.skills/MakePRForIssue/scripts/fetch-issue.py --issue-number <IssueIndex>` from the repository root. The script prints a JSON object with `number`, `title`, `body`, `url`, and `labels`. If the issue does not exist or cannot be read, write the run receipt with `"status": "error"` and stop. Treat the issue `body` as the authoritative feature specification (the same Markdown structure written by `IssueWhatWeJustDiscussed`). Warn the user if the `theloop` label is missing, but continue unless the issue body is empty.

4. **Prepare the branch.** From the repository root, update the default branch: `git fetch origin` and check out a clean, up-to-date base (typically `main` or `master` — use whichever exists and tracks `origin`). Derive a short, memorable branch name from the issue title: lowercase, words separated by hyphens, no special characters, at most 40 characters (for example, `add-issue-pr-skill` for "Add MakePRForIssue skill"). If the first candidate is taken, append `-2`, `-3`, and so on until free. Run `.skills/MakePRForIssue/scripts/check-branch.py --branch <candidate>` for each candidate; the script exits 0 when the branch is available both locally and on the remote, and prints JSON with `"available": true`. When a name is free, run `git checkout -b <branch>`. Journal: post `started working; chose branch \`<branch>\`` via `issue-comment.py`.

5. **Write the feature design document.** Before writing implementation code, create a Markdown design document at an appropriate path within the repository — use `docs/<FeatureName>.md` if a `docs/` directory exists, otherwise `FEATURE.md` at the repository root. Base it on the issue body. The document must contain:
   - A title and one-paragraph summary
   - The rationale for the design
   - An implementation outline: key components, responsibilities, and interactions
   - A "how to rebuild" section so the feature can be reconstructed from the document alone

   Record the chosen path for the run receipt.

6. **Implement the feature.** Using the issue body and the design document as the specification, write or modify the source files needed to realize the feature. Keep code, configuration, and tests consistent with the design document.

7. **Run PreCommitSkill.** Journal: `running the checks`. Invoke the `PreCommitSkill` skill, passing no parameters. Invoke it through the configured skill runner if one is available; otherwise execute it by reading `.skills/PreCommitSkill/SKILL.md` and following its instructions literally. Record the `SkillRunId` that `PreCommitSkill` generates and whether its final verdict was `"pass"`.

8. **Evaluate the outcome.**
   - If `PreCommitSkill` reported `"pass"`, proceed to step 10.
   - If it reported `"fail"` or `"error"`, proceed to the fix loop (step 9).

9. **Fix loop.** While `PreCommitSkill` has not reported `"pass"`, and fewer than five total `PreCommitSkill` invocations have occurred in this run:
   a. Journal: `fixing …` — summarize what failed.
   b. Read every failing check from the most recent `PreCommitSkill` receipt and its sub-run receipts.
   c. Fix the root cause; align implementation with the design document, updating the document first when it must change.
   d. Do not remove or weaken a check to make it pass.
   e. Journal: `running the checks`, then invoke `PreCommitSkill` again (step 7) and re-evaluate (step 8).

   If `PreCommitSkill` has still not reported `"pass"` after five total invocations, write the run receipt with `"status": "fail"` and stop.

10. **Commit and push.** Stage and commit every change on the branch with a clear commit message referencing the issue (for example, `Implement feature for #<IssueIndex>`). If the work required multiple commits during the fix loop, that is fine — journal every new commit SHA on the branch. Run `git push -u origin <branch>`.

11. **Create the pull request.** Build a PR body and save it to `tmp/<SkillRunId>-pr-body.md`. The body **must** include all of the following:
   - A prominent notice that **this pull request was created by theloop** (for example, a blockquote near the top: `> This pull request was created by **theloop**.`).
   - A statement that **this PR implements issue #\<IssueIndex\>** (substitute the issue number), with a Markdown link to the issue URL from step 3.
   - A pointer that the **problem statement, acceptance criteria, and design decisions** are recorded in that issue — reviewers should read the issue for full context rather than duplicating the entire spec in the PR.
   - `Closes #<IssueIndex>` so merging closes the issue.
   - A brief summary of what was implemented in this PR.
   - The path to the feature design document written in step 5.

   Use this structure (adapt placeholders; keep the theloop notice and issue pointer):

   ```markdown
   > This pull request was created by **theloop**.

   This PR implements issue #<IssueIndex> — [<issue title>](<issue_url>).

   The problem statement, acceptance criteria, and design decisions are recorded in that issue; read it for full context.

   Closes #<IssueIndex>

   ## Summary
   One or two paragraphs on what this PR changes.

   ## Design document
   `<feature_doc_path>`
   ```

   Run `.skills/MakePRForIssue/scripts/create-pr.py` with `--title TITLE` (the issue title, or a concise variant), `--body-file tmp/<SkillRunId>-pr-body.md`, and `--head <branch>`. The script creates a PR with the `theloop` label and prints JSON with `pr_number` and `pr_url`. Journal: `created PR #<pr_number> — <pr_url>`.

12. **Final report.** Tell the user:
    - That the pull request was created successfully
    - The PR number and full PR URL — prominently, on their own lines
    - The branch name and issue URL
    - The path of the feature design document
    - The `SkillRunId` of this run and the `SkillRunId` of the final `PreCommitSkill` run
    - A brief summary of what was implemented

13. **Write the run receipt** by calling `.skills/MakePRForIssue/scripts/write-receipt.py` with CLI flags: `--skill-run-id`, `--status pass|fail|error`; when status is `pass`: `--issue-number N`, `--issue-url URL`, `--branch NAME`, `--pr-number N`, `--pr-url URL`, `--feature-doc-path PATH`, `--implementation-attempts N`, `--pre-commit-skill-run-id ID`, `--gh-check-sub-run-id ID`, and `--commits "sha1 sha2 ..."` (space-separated short SHAs of commits on this branch not on the base); when status is `fail`: include whatever fields were determined before failure; when status is `error`: `--error TEXT`. The script validates the schema and refuses to overwrite an existing receipt.

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.json` must have exactly these fields:

```json
{
  "skill_run_id": "string — the generated SkillRunId",
  "skill": "MakePRForIssue",
  "status": "pass | fail | error",
  "issue_number": "integer|null — the IssueIndex parameter, null when status is error before the issue was loaded",
  "issue_url": "string|null — the GitHub issue URL, null when unavailable",
  "branch_name": "string|null — the branch used for implementation, null when not created",
  "pr_number": "integer|null — the GitHub pull request number, null when no PR was created",
  "pr_url": "string|null — the full GitHub pull request URL, null when no PR was created",
  "feature_doc_path": "string|null — path to the design document, null when status is error",
  "implementation_attempts": "integer|null — total PreCommitSkill invocations, null when status is error",
  "pre_commit_skill_run_id": "string|null — SkillRunId of the final PreCommitSkill run, null when status is error",
  "gh_check_sub_run_id": "string|null — InternalSkillCheckGhRepoAccessWithRunId sub-run identifier, null when status is error before that sub-run",
  "commits": ["string — short commit SHA, seven characters"] ,
  "error": "string|null — set only when status is error"
}
```

- `commits` is `[]` when no commits were made, and `null` only when `status` is `"error"` before any commit;
- `status` is `"pass"` when the PR was created and the final `PreCommitSkill` run reported `"pass"` (then `error` is `null`);
- `"fail"` when checks or PR creation failed after partial progress (then `error` is `null`);
- `"error"` when the skill could not proceed — bad parameters, missing issue, or a pre-existing receipt file (then nullable fields are `null` and `error` explains why).

**Run receipt (final reminder):** before finishing this skill — regardless of outcome, success, failure, or error alike — write `tmp/<SkillRunId>.json` containing a single well-formed JSON object conforming to the schema above. The only exception is when `tmp/<SkillRunId>.json` already existed before the run: in that case, never overwrite it.
