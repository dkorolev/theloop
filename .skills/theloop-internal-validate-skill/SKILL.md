---
name: theloop-internal-validate-skill
description: Meta-skill that validates another skill in this repository against .theloop/SKILLS-META-RULES.md. Takes a SkillRunId and the name of the skill to check; errors if the target skill does not exist, skips the validation when the cache described in .theloop/CACHING.md records a pass over unchanged inputs, otherwise reports whether the skill complies with every rule.
argument-hint: <SkillRunId> <SkillNameToCheck>
---

# theloop-internal-validate-skill

**Run receipt (write once, never overwrite):** before doing anything else, check whether the file `tmp/<SkillRunId>.json` (relative to the repository root) already exists, where `SkillRunId` is the first parameter of this skill. If it exists, refuse to run: report the error to the user and stop without touching the file. Otherwise, no matter how this skill ends — success, validation failure, or error — you must write `tmp/<SkillRunId>.json` containing exactly one well-formed JSON object following the schema in the "Run receipt schema" section below. Create the `tmp/` directory if it does not exist.

Running this skill is an operation fully contained within the directory of this repository: do not read, write, or otherwise access any file outside the repository.

## Parameters

This skill takes exactly two parameters, in this order:

1. `SkillRunId` — a random identifier for this run, supplied by the caller. Used as the run-receipt filename: `tmp/<SkillRunId>.json`. No file by that name may exist prior to the run.
2. `SkillNameToCheck` — the name of the other skill in this repository to validate.

If either parameter is missing, or extra parameters are passed, stop and report an error (and still write the run receipt with `"status": "error"`, provided `tmp/<SkillRunId>.json` did not exist before the run).

## Steps

All scripts under `.skills/theloop-internal-validate-skill/scripts/` are executable and begin with `#!/usr/bin/env python3`; run each one directly by path — never prefix it with `python` or `python3`.

1. **Confirm the target skill exists.** Look for `.skills/<SkillNameToCheck>/SKILL.md` in this repository. If it does not exist, this run is an error: report it to the user, write the run receipt with `"status": "error"` and an explanatory `"error"` message, and stop.
2. **Probe the validation cache.** Per the rule on hashing and caching of slow checks, run `.skills/theloop-internal-validate-skill/scripts/cache.py probe <SkillNameToCheck>` from the repository root. It computes the fingerprint described in `.theloop/CACHING.md` — the input set is every non-ignored file under `.skills/<SkillNameToCheck>/` plus `.theloop/SKILLS-META-RULES.md`, `SKILLS.md`, and `.theloop/VIZ.md`, under the check name `theloop-internal-validate-skill:<SkillNameToCheck>` — and reports whether a cache entry exists. On a cache hit (`"cached": true`), this exact validation has already passed over byte-identical inputs: skip the remaining validation steps entirely — do not read the rules or the target skill — report to the user that the skill is compliant per the cache, and proceed directly to writing the run receipt with `"status": "pass"` and `"source": "cache"`.
3. **Read the skills meta-rules.** Read `.theloop/SKILLS-META-RULES.md`, under the `.theloop/` directory at the repository root. Every meta-rule in that file applies to the target skill.
4. **Run the mechanical checks.** Run `.skills/theloop-internal-validate-skill/scripts/mechanical-checks.py <SkillNameToCheck>` from the repository root. It checks the mechanically verifiable projections of the rules and prints the outcomes as JSON:
   - for the rule on containment within the repo, that the target skill states that running it is fully contained within the repository directory;
   - for the rule on run receipts, that the target skill declares `SkillRunId` as its first parameter or explicitly states that it is an exception that takes no `SkillRunId`; when it takes the parameter, that its instruction body **begins** and **ends** with the instruction to write but never overwrite `tmp/<SkillRunId>.json`, and that it describes the fixed JSON schema of that receipt; and when it generates a `SkillRunId` itself, rather than receiving it from its caller, that it prescribes the default format codified in that rule;
   - for the rule on the `SKILLS.md` file and the rule on visualization and topology, their per-skill projection: the target skill is listed in `SKILLS.md`, and is listed in `.theloop/VIZ.md` together with all of its actual invocation relationships. Checking the other direction — that nothing extra is listed — is a whole-repo property and is out of scope for this single-skill check;
   - for the rule on referring to rules by name, that the target skill never references a rule by its number;
   - for the rule on internal skill naming, that skills taking `SkillRunId` begin with `theloop-internal-` and user-facing skills do not;
   - for the rule on use of scripts, that every script the target skill references exists at the referenced path.

   The script reads invocations from the `invokes` field in the target skill's frontmatter, so its output is unambiguous; treat every reported failure as a genuine violation.
5. **Judge the remaining rules.** Read the target skill's `SKILL.md` and check what the script cannot:
   - For the rule on strict parameters, verify that the target skill declares exactly which parameters it takes and instructs the runner to validate them before executing, and that any invocations of other skills pass exactly the right parameters. In particular, verify that it refuses to run, with an error, if `tmp/<SkillRunId>.json` exists prior to the run.
   - For the rule on the universal directory for skills, note that the first step already enforces it structurally: a skill anywhere else than under `.skills/` is not found at all.
   - For the rule on use of scripts, verify that any non-trivial code the target skill runs is provided as scripts under `.skills/<SkillNameToCheck>/scripts/` rather than written as ad-hoc temporary files.
   - For the rule on taste and style, verify that the target skill's text is free of grammatical errors and easy to read, and that any provided scripts are understandable, follow simple input/output formats, perform no surprising operations, and keep their error messages short yet complete.
   - For the rule on parallel invocation of spawned skills, verify that if the target skill invokes other skills: when it starts two or more independent sub-runs, it instructs the runner to fan out subagents (one subagent per sub-run) and aggregate receipts after all complete; when parallel execution is undesirable, it explains in detail why; when it invokes exactly one other skill, no parallelism wording is required.
   - For the rules on persistent repository artifacts, atomic, idempotent state mutation, and time-bounded operations, verify each where it applies to the target skill: a skill that maintains a durable, committed artifact declares its single root path, writes an ownership marker there, keeps the artifact compact, and refuses to adopt a root it did not create; every durable mutation goes through a provided script that writes atomically and idempotently and guards against lost updates; and the skill never waits on anything unboundedly — any fanned-out sub-runs are bounded with a timeout-as-error fallback (a sub-run past its bound, or with no receipt, is a timeout), and any provided script that makes a blocking call, such as a subprocess or a network request, imposes its own timeout and exits with a short timeout error. A skill with no durable artifact and no blocking waits complies with these trivially.
   - For the rule on splitting slow work into collect-then-analyze, verify — where the target skill does slow or journaled-from-a-stream work — that it caches the slow collection step (gitignored, keyed cleanly by input identity, written via temp file plus atomic rename) for reuse across runs, and marks an input processed only after its durable output is committed. Trivial for skills whose work is neither slow nor streamed.
   - For the rule on hashing and caching of slow checks, verify that if the target skill performs checks that are slow or token-consuming and fully determined by a fixed set of files, it uses the caching technique from `.theloop/CACHING.md` with a provided Python script — not an inline reimplementation — to compute fingerprints.
   - For the rule on visualization and topology, verify that the `invokes:` field in the target skill's frontmatter is bidirectionally accurate: every skill named in `invokes:` is one that the instruction body actually directs the runner to invoke, and every skill the instruction body directs the runner to invoke is listed in `invokes:`. A name in `invokes:` with no matching invocation in the instructions is a phantom entry; an invocation in the instructions with no matching `invokes:` entry is an omission. Both are violations.
6. **Write the validation cache.** If the verdict is `"pass"` (no violations), run `.skills/theloop-internal-validate-skill/scripts/cache.py write <SkillNameToCheck>` from the repository root. It recomputes the fingerprint and writes the cache entry under `tmp/caches/`; it is idempotent if the entry already exists.
7. **Report.** Tell the user whether the skill passes, listing each violation (rule and detail) if it does not. When the verdict came from the cache (step 2), report that clearly.
8. **Write the run receipt** by calling `.skills/theloop-internal-validate-skill/scripts/write-receipt.py` with CLI flags: `--skill-run-id`, `--checked-skill`, `--status`, and (when status is not `error`) `--source cache|regenerated`; add `--violations-json '[...]'` when status is `fail`; add `--error TEXT` when status is `error`. The script validates the schema and refuses to overwrite an existing receipt.

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.json` must have exactly these fields:

```json
{
  "skill_run_id": "string — the SkillRunId parameter, verbatim",
  "skill": "theloop-internal-validate-skill",
  "checked_skill": "string|null — the SkillNameToCheck parameter, or null if it was missing",
  "status": "pass | fail | error",
  "source": "cache | regenerated | null — cache when the pass verdict was served from the cache, regenerated when validation ran in full, null when status is error",
  "violations": [
    { "rule": "string — the name of the violated rule, as it is titled in .theloop/SKILLS-META-RULES.md", "detail": "string — what is violated and where" }
  ],
  "error": "string|null — set only when status is 'error' (e.g. target skill not found)"
}
```

- `status` is `"pass"` when the target skill exists and satisfies every rule (then `violations` is `[]` and `error` is `null`); `"source"` is `"cache"` when the verdict came from the cache, `"regenerated"` when the full validation ran;
- `"fail"` when it exists but violates at least one rule (then `violations` is non-empty and `"source"` is `"regenerated"`);
- `"error"` when validation could not be performed at all (then `error` explains why and `"source"` is `null`).

**Run receipt (final reminder):** before finishing this skill — regardless of outcome, success or error alike — write `tmp/<SkillRunId>.json` containing a single well-formed JSON object conforming to the schema above. The only exception is when `tmp/<SkillRunId>.json` already existed before the run: in that case refuse to run and never overwrite it.
