---
name: PreCommitSkillForClientRepos
description: Meta-skill that gates a commit to a theloop client repository. Takes no parameters and errors if any are passed; checks that newrepo-theloopify-internal-postinit has been completed, generates a fresh SkillRunId in the default format codified in .theloop/SKILLS-META-RULES.md, and delegates the slim pre-commit gate to InternalSkillPreCommitForClientWithRunId under that identifier.
invokes: [InternalSkillPreCommitForClientWithRunId]
---

# PreCommitSkillForClientRepos

This skill is the parameterless entry point of the pre-commit gate in a theloop client repository: it confirms the repository has been configured, generates a run identifier, and delegates all checks to `InternalSkillPreCommitForClientWithRunId`. Per the rule on run receipts, this is the exceptional skill that does not take the `SkillRunId` parameter — it is invoked by a human (or another workflow skill) before a commit, where a caller-supplied identifier would serve no purpose. It writes no run receipt of its own: the entire run is performed and receipted by the `InternalSkillPreCommitForClientWithRunId` sub-run it spawns, under the generated identifier.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository.

## Parameters

This skill takes no parameters. If any parameters are passed, stop immediately and report an error: do not check configuration, do not generate an identifier, and do not invoke `InternalSkillPreCommitForClientWithRunId`.

## Steps

The scripts under `.skills/PreCommitSkillForClientRepos/scripts/` are executable; run each one directly by path — never prefix it with `python`, `python3`, or `sh`.

1. **Check the configuration gate.** Run `.skills/PreCommitSkillForClientRepos/scripts/check-configured.py` from the repository root. It reports whether this repository has completed `newrepo-theloopify-internal-postinit`, keying off the positive marker `.theloop/configure_the_loop.done`. If it exits non-zero (`"configured": false`), stop immediately: tell the user the repository is not configured yet and that they must run `newrepo-theloopify-internal-postinit` before committing. Do not generate an identifier and do not delegate. When it reports configured (including the not-applicable case in a non-theloopified repository), continue.

2. **Generate the run identifier.** Run `.skills/PreCommitSkillForClientRepos/scripts/new-run-id.sh` from the repository root: it prints a fresh `SkillRunId` in the default format codified in the rule on run receipts, `YYYYMMDD-HHMMSS-{six_random_latin_lowercase_characters}` — the local date and time at which the run started, followed by six random lowercase Latin letters (for example, `20260607-153012-kqzwxy`). Tell the user which identifier was generated.

3. **Delegate.** Invoke the `InternalSkillPreCommitForClientWithRunId` skill, passing exactly one parameter: the generated `SkillRunId`. Invoke it through the configured skill runner if one is available; otherwise execute it by reading `.skills/InternalSkillPreCommitForClientWithRunId/SKILL.md` and following its instructions literally.

4. **Relay the verdict.** Read the run receipt `tmp/<SkillRunId>.json` written by `InternalSkillPreCommitForClientWithRunId` and relay its verdict to the user: the commit may proceed only when its `status` is `"pass"`; otherwise report every reason the commit is blocked, as recorded in that receipt — each failing hygiene check and each failing `PRECOMMIT.md` check, with its detail.
