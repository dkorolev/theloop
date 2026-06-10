---
name: theloop-buildthis
description: Summarizes the current conversation to extract the feature request, implements the feature with a design document, then runs theloop-precommit and iterates on any failures until the implementation is complete and all pre-commit checks pass.
invokes: [theloop-precommit]
---

# theloop-buildthis

Per the rule on run receipts, this is the exceptional skill that does not take the `SkillRunId` parameter — it is invoked by a human at the end of a design discussion, where a caller-supplied identifier would serve no purpose. It generates a fresh `SkillRunId` of its own and writes its own run receipt.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository. The one exception is that it queries your configured `git` author identity (`git config user.name` and `git config user.email`), which `git` itself may resolve from your global configuration.

## Parameters

This skill takes no parameters. If any parameters are passed, stop immediately and report an error.

## Steps

The Python scripts under `.skills/theloop-buildthis/scripts/` are executable and begin with `#!/usr/bin/env python3`; run each one directly by path — never prefix it with `python` or `python3`.

1. **Check the configuration gate and git identity, then generate the run identifier.** First run `.skills/theloop-buildthis/scripts/check-configured.py` from the repository root. If it exits non-zero (the repository has been theloopified but `newrepo-theloopify-internal-postinit` has not completed), stop immediately: tell the user they must run `newrepo-theloopify-internal-postinit` before implementing, and do not generate an identifier. When it reports configured — including the not-applicable case in a non-theloopified repository, such as the theloop repository itself — continue. Next, confirm a git author identity is configured: run `git config user.name` and `git config user.email`. If either prints nothing (unset or empty), stop immediately — tell the user to set their git identity first (for example, `git config --global user.name "Your Name"` and `git config --global user.email "you@example.com"`) before re-running this skill, since the staged implementation must afterward be committed under their identity — and do not generate an identifier. When both are set, continue. Then run `.skills/theloop-buildthis/scripts/new-run-id.sh` from the repository root: it prints a fresh `SkillRunId` in the default format codified in the rule on run receipts, `YYYYMMDD-HHMMSS-{six_random_latin_lowercase_characters}` — the local date and time at which the run started, followed by six random lowercase Latin letters (for example, `20260607-153012-kqzwxy`). Tell the user which identifier was generated. Then confirm that `tmp/<SkillRunId>.json` does not already exist; if it does, stop immediately and report an error without touching the file.

2. **Summarize the conversation.** Review the entire current conversation — all turns visible to the outer shell running this skill — and produce a feature specification:
   - The feature the user wants built, expressed as a concrete, unambiguous goal
   - Key design decisions or constraints mentioned in the conversation
   - Specific behavior or interface requirements
   - How a passing result will be recognized

   If the conversation does not contain a clear feature request, write the run receipt with `"status": "error"` and stop: report to the user that no feature request was found and ask them to describe what to build before invoking this skill again.

3. **Write the feature design document.** Before writing any implementation code, create a Markdown design document. This is a deliberate, encouraged practice — do not skip it. Give the file a **feature-specific filename** derived from the feature you extracted from the conversation (for example, `dark-mode-toggle.md` or `csv-export.md`) — never a generic name such as `FEATURE.md` or `DESIGN-DOC.md`. Place it following the repository's existing convention for design documents: in a dedicated design-docs directory if one exists (such as `design-docs/`, `docs/design/`, or `docs/`), or alongside the code the feature touches when that is the established pattern. If the repository has no such convention, create a top-level `design-docs/` directory and put the document there. The document must contain:
   - A title and one-paragraph summary of the feature
   - The rationale for the design: why this approach, drawn from the conversation
   - An implementation outline: the key components, their responsibilities, and how they interact
   - A "how to rebuild" section describing what the code must do, what invariants it must satisfy, and what a correct reimplementation looks like — written so the feature can be reconstructed from this document alone if the code is ever lost

   Record the chosen path; it goes in the run receipt. Write this document carefully: it is the durable specification, and the implementation must remain consistent with it throughout this run and any future ones.

4. **Implement the feature.** Using the conversation summary and the design document as the authoritative specification, write or modify the source files needed to realize the feature. Keep implementation code, configuration, and tests consistent with each other and with the design document.

5. **Run theloop-precommit.** Invoke the `theloop-precommit` skill, passing no parameters. Invoke it through the configured skill runner if one is available; otherwise execute it by reading `.skills/theloop-precommit/SKILL.md` and following its instructions literally. Record the `SkillRunId` that `theloop-precommit` generates (it reports this identifier at the start of its run), and record whether its final verdict was `"pass"` or not.

6. **Evaluate the outcome.**
   - If `theloop-precommit` reported `"pass"`, proceed to staging the changes (step 8).
   - If it reported `"fail"` or `"error"`, proceed to the fix loop (step 7).

7. **Fix loop.** While `theloop-precommit` has not reported `"pass"`, and fewer than five total `theloop-precommit` invocations have occurred in this run:
   a. Read every failing check from the most recent `theloop-precommit` receipt and its sub-run receipts.
   b. For each failing check, identify the root cause. If the implementation diverges from the design document, correct the implementation to match the document. If the design document itself needs revision to reflect a necessary change, update it first and then bring the implementation into alignment.
   c. Do not remove or weaken a check to make it pass; fix the underlying cause so the check genuinely holds.
   d. Invoke the `theloop-precommit` skill again (step 5) and re-evaluate (step 6).

   If `theloop-precommit` has still not reported `"pass"` after five total invocations, write the run receipt with `"status": "fail"` and stop: report every remaining blocking issue to the user in full.

8. **Stage the implemented changes.** Run `.skills/theloop-buildthis/scripts/stage-allowed.py` from the repository root: it stages every change except the paths listed in `.theloop/do_not_commit.txt`, so theloop instrumentation (the `.theloop/` scaffolding, the agent skill symlinks, `tmp/`, and the `.gitignore` change `theloopify` made) is hard-excluded and can never be staged for a feature commit. In the theloop repository itself there is no `.theloop/do_not_commit.txt`, so it stages everything. Feature design documents are user artifacts and are not excluded. Leave the changes staged but uncommitted for the user to review and commit. The resulting commit is authored by the user, never by the AI assistant: do not create the commit on the user's behalf, and the commit message must contain no AI-assistant attribution (no `Generated with …` line, no `Co-Authored-By:` trailer naming an AI assistant, model, or tool, and no other mention of the AI that produced the change).

9. **Final report.** Tell the user:
   - That the implementation is complete and all pre-commit checks pass
   - The path of the feature design document
   - The `SkillRunId` of this run and the `SkillRunId` of the final `theloop-precommit` run
   - A brief summary of what was implemented

10. **Write the run receipt** by calling `.skills/theloop-buildthis/scripts/write-receipt.py` with CLI flags: `--skill-run-id`, `--status pass|fail|error`; when status is not `error`: `--feature-summary TEXT`, `--feature-doc-path PATH`, `--implementation-attempts N`, `--pre-commit-skill-run-id ID`; when status is `error`: `--error TEXT`. The script validates the schema and refuses to overwrite an existing receipt.

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.json` must have exactly these fields:

```json
{
  "skill_run_id": "string — the generated SkillRunId",
  "skill": "theloop-buildthis",
  "status": "pass | fail | error",
  "feature_summary": "string|null — one-sentence summary of what was built, null when status is error",
  "feature_doc_path": "string|null — path to the feature design document written during this run, null when status is error",
  "implementation_attempts": "integer|null — total number of theloop-precommit invocations in this run, null when status is error",
  "pre_commit_skill_run_id": "string|null — the SkillRunId generated by the final theloop-precommit invocation, null when status is error",
  "error": "string|null — set only when status is error"
}
```

- `status` is `"pass"` when the implementation is complete and the final `theloop-precommit` run reported `"pass"` (then `error` is `null`);
- `"fail"` when the fix loop was exhausted without a passing `theloop-precommit` run (then `error` is `null`);
- `"error"` when this skill could not proceed at all — for example, unexpected parameters were supplied, no feature request was found in the conversation, or a pre-existing receipt file was detected (then `feature_summary`, `feature_doc_path`, `implementation_attempts`, and `pre_commit_skill_run_id` are `null`, and `error` explains why).

**Run receipt (final reminder):** before finishing this skill — regardless of outcome, success, failure, or error alike — write `tmp/<SkillRunId>.json` containing a single well-formed JSON object conforming to the schema above. The only exception is when the run was aborted because `tmp/<SkillRunId>.json` already existed before the run: in that case, never overwrite it.
