---
name: theloop-makeissue
description: Summarizes the current conversation into a complete feature description, asks the human for clarifications until the picture is clear, verifies GitHub CLI access, then creates a GitHub issue tagged with theloop. Use when the user wants to capture a feature discussion as a tracked issue, file a feature request from a design conversation, or turn what was just discussed into a GitHub issue.
invokes: [theloop-internal-check-gh-repo-access]
---

# theloop-makeissue

Per the rule on run receipts, this is the exceptional skill that does not take the `SkillRunId` parameter — it is invoked by a human at the end of a design discussion, where a caller-supplied identifier would serve no purpose. It generates a fresh `SkillRunId` of its own and writes its own run receipt.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository. The `gh` commands below reach GitHub over the network but do not touch paths outside this repository.

## Parameters

This skill takes no parameters. If any parameters are passed, stop immediately and report an error.

## Steps

The Python scripts under `.skills/theloop-makeissue/scripts/` are executable and begin with `#!/usr/bin/env python3`; run each one directly by path — never prefix it with `python` or `python3`.

1. **Check the configuration gate, then generate the run identifier.** First run `.skills/theloop-makeissue/scripts/check-configured.py` from the repository root. If it exits non-zero (the repository has been theloopified but `newrepo-theloopify-internal-postinit` has not completed), stop immediately: tell the user they must run `newrepo-theloopify-internal-postinit` before capturing an issue, and do not generate an identifier. When it reports configured — including the not-applicable case in a non-theloopified repository, such as the theloop repository itself — continue. Then run `.skills/theloop-makeissue/scripts/new-run-id.sh` from the repository root: it prints a fresh `SkillRunId` in the default format codified in the rule on run receipts, `YYYYMMDD-HHMMSS-{six_random_latin_lowercase_characters}` — the local date and time at which the run started, followed by six random lowercase Latin letters (for example, `20260607-153012-kqzwxy`). Tell the user which identifier was generated. Then confirm that `tmp/<SkillRunId>.json` does not already exist; if it does, stop immediately and report an error without touching the file.

2. **Verify GitHub access.** Invoke the `theloop-internal-check-gh-repo-access` skill with exactly one parameter: the sub-run identifier `<SkillRunId>-theloop-internal-check-gh-repo-access`. Invoke it through the configured skill runner if one is available; otherwise execute it by reading `.skills/theloop-internal-check-gh-repo-access/SKILL.md` and following its instructions literally. Read the sub-run receipt at `tmp/<SkillRunId>-theloop-internal-check-gh-repo-access.json`. If its `status` is not `"pass"`, relay every failing check and its remediation suggestion to the user, write the run receipt with `"status": "fail"`, and stop without creating an issue.

3. **Extract the feature from the conversation.** Review the entire current conversation — all turns visible to the outer shell running this skill — and determine what feature the user wants built. If the conversation contains no feature discussion at all, write the run receipt with `"status": "error"` and stop: report to the user that no feature request was found and ask them to describe what to build before invoking this skill again.

4. **Clarify until the picture is clear.** Before writing the final specification or creating an issue, make sure you understand the feature well enough that an engineer could implement it without guessing. When anything is ambiguous, incomplete, or contradictory — scope, behavior, edge cases, acceptance criteria, constraints, or how success will be recognized — ask the human specific, numbered clarifying questions. Do not create the GitHub issue while material questions remain unanswered. When you need clarification, stop after asking; do not write the run receipt yet. When the human replies, resume from this step with their answers incorporated.

5. **Draft the feature specification.** Once the feature is clear, write a Markdown specification using this structure:

   ```markdown
   # [Feature title]

   ## Summary
   One paragraph describing the feature and the outcome it delivers.

   ## Problem / motivation
   Why this feature is needed, drawn from the conversation.

   ## Proposed behavior
   Detailed description of what the system should do — interfaces, flows, and edge cases.

   ## Acceptance criteria
   - Criterion 1 — concrete and testable
   - Criterion 2
   - …

   ## Design notes and constraints
   Decisions, non-goals, dependencies, or limits mentioned in the conversation.

   ## Open questions
   Remaining uncertainties, or "None" when everything is settled.
   ```

   Use plain Markdown bullets throughout the specification — never task-list checkboxes (`- [ ]`); these issues are not checked off interactively, so checkboxes only add noise.

   Present the draft specification to the user and ask whether it accurately captures what should be built. If they request changes, revise the draft and ask again. Do not proceed until the user confirms the specification is correct.

6. **Create the GitHub issue.** Save the confirmed specification to `tmp/<SkillRunId>-issue-body.md` in the repository. Derive a concise issue title from the feature (the `#` heading in the specification, without the leading `#`). Run `.skills/theloop-makeissue/scripts/create-issue.py` from the repository root with CLI flags `--title TITLE` and `--body-file tmp/<SkillRunId>-issue-body.md`. The script reads the repository URL from `.theloop/repo.txt`, creates an issue with the `theloop` label, and prints a JSON object with `issue_number` and `issue_url`. If the script exits non-zero, relay the error to the user, write the run receipt with `"status": "fail"`, and stop.

7. **Final report.** Tell the user:
   - That the GitHub issue was created successfully
   - The issue number (ID) and the full issue URL — both prominently, on their own lines
   - A one-sentence summary of the feature captured in the issue
   - The `SkillRunId` of this run
   - That they can implement the feature and open a pull request by running `/theloop-fixissue <issue_number>` (substitute the issue number just created)

8. **Write the run receipt** by calling `.skills/theloop-makeissue/scripts/write-receipt.py` with CLI flags: `--skill-run-id`, `--status pass|fail|error`; when status is `pass`: `--feature-title TITLE`, `--feature-summary TEXT`, `--issue-number N`, `--issue-url URL`, `--gh-check-sub-run-id ID`; when status is `fail`: `--gh-check-sub-run-id ID` if the GitHub access sub-run completed, plus any of `--issue-number` and `--issue-url` if an issue was partially created; when status is `error`: `--error TEXT`. The script validates the schema and refuses to overwrite an existing receipt.

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.json` must have exactly these fields:

```json
{
  "skill_run_id": "string — the generated SkillRunId",
  "skill": "theloop-makeissue",
  "status": "pass | fail | error",
  "feature_title": "string|null — the issue title, null when status is error",
  "feature_summary": "string|null — one-sentence summary of the feature, null when status is error",
  "issue_number": "integer|null — the GitHub issue number, null when no issue was created",
  "issue_url": "string|null — the full GitHub issue URL, null when no issue was created",
  "gh_check_sub_run_id": "string|null — the theloop-internal-check-gh-repo-access sub-run identifier, null when status is error before the sub-run started",
  "error": "string|null — set only when status is error"
}
```

- `status` is `"pass"` when the issue was created successfully (then `error` is `null` and `issue_number` and `issue_url` are set);
- `"fail"` when GitHub access checks failed or issue creation failed (then `error` is `null`);
- `"error"` when this skill could not proceed at all — for example, unexpected parameters were supplied, no feature request was found in the conversation, or a pre-existing receipt file was detected (then `feature_title`, `feature_summary`, `issue_number`, and `issue_url` are `null`, and `error` explains why).

**Run receipt (final reminder):** before finishing this skill — regardless of outcome, success, failure, or error alike — write `tmp/<SkillRunId>.json` containing a single well-formed JSON object conforming to the schema above. The only exception is when the run was aborted because `tmp/<SkillRunId>.json` already existed before the run, or when the skill is paused waiting for clarifications or user confirmation: in those cases, do not write the receipt yet. The only exception to never overwriting is when `tmp/<SkillRunId>.json` already existed before the run: in that case, never overwrite it.
