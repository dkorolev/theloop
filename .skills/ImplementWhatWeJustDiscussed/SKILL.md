---
name: ImplementWhatWeJustDiscussed
description: Summarizes the current conversation to extract the feature request, implements the feature with a design document, then runs PreCommitSkill and iterates on any failures until the implementation is complete and all pre-commit checks pass.
---

# ImplementWhatWeJustDiscussed

Per the rule on run receipts, this is the exceptional skill that does not take the `SkillRunId` parameter — it is invoked by a human at the end of a design discussion, where a caller-supplied identifier would serve no purpose. It generates a fresh `SkillRunId` of its own and writes its own run receipt.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository.

## Parameters

This skill takes no parameters. If any parameters are passed, stop immediately and report an error.

## Steps

1. **Generate the run identifier.** Run `.skills/ImplementWhatWeJustDiscussed/scripts/new-run-id.sh` from the repository root: it prints a fresh `SkillRunId` in the default format codified in the rule on run receipts, `YYYYMMDD-HHMMSS-{six_random_latin_lowercase_characters}` — the local date and time at which the run started, followed by six random lowercase Latin letters (for example, `20260607-153012-kqzwxy`). Tell the user which identifier was generated. Then confirm that `tmp/<SkillRunId>.json` does not already exist; if it does, stop immediately and report an error without touching the file.

2. **Summarize the conversation.** Review the entire current conversation — all turns visible to the outer shell running this skill — and produce a feature specification:
   - The feature the user wants built, expressed as a concrete, unambiguous goal
   - Key design decisions or constraints mentioned in the conversation
   - Specific behavior or interface requirements
   - How a passing result will be recognized

   If the conversation does not contain a clear feature request, write the run receipt with `"status": "error"` and stop: report to the user that no feature request was found and ask them to describe what to build before invoking this skill again.

3. **Write the feature design document.** Before writing any implementation code, create a Markdown design document at an appropriate path within the repository. Choose the path that fits the project's existing conventions: use `docs/<FeatureName>.md` if a `docs/` directory exists, otherwise `FEATURE.md` at the repository root. The document must contain:
   - A title and one-paragraph summary of the feature
   - The rationale for the design: why this approach, drawn from the conversation
   - An implementation outline: the key components, their responsibilities, and how they interact
   - A "how to rebuild" section describing what the code must do, what invariants it must satisfy, and what a correct reimplementation looks like — written so the feature can be reconstructed from this document alone if the code is ever lost

   Record the chosen path; it goes in the run receipt. Write this document carefully: it is the durable specification, and the implementation must remain consistent with it throughout this run and any future ones.

4. **Implement the feature.** Using the conversation summary and the design document as the authoritative specification, write or modify the source files needed to realize the feature. Keep implementation code, configuration, and tests consistent with each other and with the design document.

5. **Run PreCommitSkill.** Invoke the `PreCommitSkill` skill, passing no parameters. Invoke it through the configured skill runner if one is available; otherwise execute it by reading `.skills/PreCommitSkill/SKILL.md` and following its instructions literally. Record the `SkillRunId` that `PreCommitSkill` generates (it reports this identifier at the start of its run), and record whether its final verdict was `"pass"` or not.

6. **Evaluate the outcome.**
   - If `PreCommitSkill` reported `"pass"`, proceed to the final report (step 8).
   - If it reported `"fail"` or `"error"`, proceed to the fix loop (step 7).

7. **Fix loop.** While `PreCommitSkill` has not reported `"pass"`, and fewer than five total `PreCommitSkill` invocations have occurred in this run:
   a. Read every failing check from the most recent `PreCommitSkill` receipt and its sub-run receipts.
   b. For each failing check, identify the root cause. If the implementation diverges from the design document, correct the implementation to match the document. If the design document itself needs revision to reflect a necessary change, update it first and then bring the implementation into alignment.
   c. Do not remove or weaken a check to make it pass; fix the underlying cause so the check genuinely holds.
   d. Invoke the `PreCommitSkill` skill again (step 5) and re-evaluate (step 6).

   If `PreCommitSkill` has still not reported `"pass"` after five total invocations, write the run receipt with `"status": "fail"` and stop: report every remaining blocking issue to the user in full.

8. **Final report.** Tell the user:
   - That the implementation is complete and all pre-commit checks pass
   - The path of the feature design document
   - The `SkillRunId` of this run and the `SkillRunId` of the final `PreCommitSkill` run
   - A brief summary of what was implemented

9. **Write the run receipt** as described below: assemble the receipt object and pipe it to `.skills/ImplementWhatWeJustDiscussed/scripts/write-receipt.py`, which validates the schema and refuses to overwrite an existing receipt.

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.json` must have exactly these fields:

```json
{
  "skill_run_id": "string — the generated SkillRunId",
  "skill": "ImplementWhatWeJustDiscussed",
  "status": "pass | fail | error",
  "feature_summary": "string|null — one-sentence summary of what was built, null when status is error",
  "feature_doc_path": "string|null — path to the feature design document written during this run, null when status is error",
  "implementation_attempts": "integer|null — total number of PreCommitSkill invocations in this run, null when status is error",
  "pre_commit_skill_run_id": "string|null — the SkillRunId generated by the final PreCommitSkill invocation, null when status is error",
  "error": "string|null — set only when status is error"
}
```

- `status` is `"pass"` when the implementation is complete and the final `PreCommitSkill` run reported `"pass"` (then `error` is `null`);
- `"fail"` when the fix loop was exhausted without a passing `PreCommitSkill` run (then `error` is `null`);
- `"error"` when this skill could not proceed at all — for example, unexpected parameters were supplied, no feature request was found in the conversation, or a pre-existing receipt file was detected (then `feature_summary`, `feature_doc_path`, `implementation_attempts`, and `pre_commit_skill_run_id` are `null`, and `error` explains why).

**Run receipt (final reminder):** before finishing this skill — regardless of outcome, success, failure, or error alike — write `tmp/<SkillRunId>.json` containing a single well-formed JSON object conforming to the schema above. The only exception is when the run was aborted because `tmp/<SkillRunId>.json` already existed before the run: in that case, never overwrite it.
