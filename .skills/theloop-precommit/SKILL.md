---
name: theloop-precommit
description: Meta-skill that gates a commit to this repository. Takes no parameters and errors if any are passed; generates a fresh SkillRunId in the default format codified in .theloop/SKILLS-META-RULES.md and delegates the entire pre-commit gate to theloop-internal-precommit under that identifier.
invokes: [theloop-internal-precommit]
---

# theloop-precommit

This skill is the parameterless entry point of the pre-commit gate: it generates a run identifier and delegates all checks to `theloop-internal-precommit`. Per the rule on run receipts, this is the exceptional skill that does not take the `SkillRunId` parameter — it is invoked by a human before a commit, where a caller-supplied identifier would serve no purpose. It writes no run receipt of its own: the entire run is performed and receipted by the `theloop-internal-precommit` sub-run it spawns, under the generated identifier.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository.

## Parameters

This skill takes no parameters. If any parameters are passed, stop immediately and report an error: do not generate an identifier and do not invoke `theloop-internal-precommit`.

## Steps

1. **Generate the run identifier.** Run `.skills/theloop-precommit/scripts/new-run-id.sh` from the repository root: it prints a fresh `SkillRunId` in the default format codified in the rule on run receipts, `YYYYMMDD-HHMMSS-{six_random_latin_lowercase_characters}` — the local date and time at which the run started, followed by six random lowercase Latin letters (for example, `20260607-153012-kqzwxy`). Tell the user which identifier was generated.
2. **Delegate.** Invoke the `theloop-internal-precommit` skill, passing exactly one parameter: the generated `SkillRunId`. Invoke it through the configured skill runner if one is available; otherwise execute it by reading `.skills/theloop-internal-precommit/SKILL.md` and following its instructions literally.
3. **Relay the verdict.** Read the run receipt `tmp/<SkillRunId>.json` written by `theloop-internal-precommit` and relay its verdict to the user: the commit may proceed only when its `status` is `"pass"`; otherwise report every reason the commit is blocked, as recorded in that receipt and in the deeper sub-run receipts it points to. Include `cache_summary` from the receipt so the user can see how many agentic checks were cached versus re-run.
