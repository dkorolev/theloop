# Rules for Skills

Every skill in this repository must comply with all of the rules below. The `ValidateSkill` skill checks compliance. The `ValidateAllSkills` skill checks compliance of all skills.

This file lives at `.ai/RULES.md`, under the `.ai/` directory in the root of the repo. All file paths in this file are relative to the root of the repo.

## Rule 1: Contained within the repo

Every skill should mention that running the skill is an operation that is fully contained within the directory of the repository. The agentic runner of the skill should not need to access files outside the repository, and it should not attempt to access files outside the repository.

## Rule 2: Strict with parameters

Every skill should have strict run semantics, such as "this skill takes two arguments, the `SkillRunId` and the `OtherSkillName`". Prior to executing itself, every skill must check that the parameters are correctly passed along.

Moreover, validation should take place beyond the number of parameters. For instance, the skill should instruct the runner that for a given `SkillRunId`, no `tmp/${SkillRunId}.json` file should exist in the repository.

Furthermore, when a skill is executing other skills, it should make sure to pass just the right parameters, in the right quantity and order.

## Rule 3: Strict with output in the form of Run Receipts

Most skills must take the `SkillRunId` as the first parameter. The skills that do not require this parameter should explicitly state so in their body, that this is the exceptional one that does not require the `SkillRunId` parameter.

The default format of a `SkillRunId` is `YYYYMMDD-HHMMSS-{six_random_latin_lowercase_characters}`: the local date and time at which the run started, followed by six random lowercase Latin letters — for example, `20260607-153012-kqzwxy`. A skill that generates a `SkillRunId` itself, rather than receiving it from its caller, must generate it in this format. Sub-run identifiers are not generated from scratch but derived, by suffixing the parent's `SkillRunId` as the invoking skill prescribes.

For skills with the `SkillRunId` parameter, the skill should explicitly mention several things:

* The skill should refuse to run, and result in an error, if the `tmp/${SkillRunId}.json` file exists prior to the skill being run.
* Except the very error that the `tmp/${SkillRunId}.json` file exists prior to running the skill, running the skill, no matter whether it results in success or in error, must produce the `tmp/${SkillRunId}.json` file, in addition to providing English-first output.
* The resulting `tmp/${SkillRunId}.json` receipt file should be of fixed schema, which is either `{"error":"..."}`, or other valid schemas provided exhaustively in the definition of the skill.

Specifically, for every skill that does take the `SkillRunId` as the parameter, the very rule to write but not overwrite the `tmp/${SkillRunId}.json` file must be present in the skill definition at least twice: once closer to the beginning of the skill, and once towards the very end of it.

Concretely, a skill that takes the `SkillRunId` parameter complies with this rule when all of the following hold:

1. The skill declares `SkillRunId` as one of its parameters.
2. The first instruction of the skill body tells the model to write `tmp/<SkillRunId>.json` upon completion.
3. The last instruction of the skill body repeats that same requirement.
4. The skill describes the JSON schema of the object that goes into `tmp/<SkillRunId>.json`.

Note that the `tmp/` directory is `.gitignore`-d, so skill run receipts are never committed. The `PreCommitSkillWithRunId` skill must check this.

## Rule 4: Universal directory for skills

The skills live under the `.skills/` directory in the root of the repo.

## Rule 5: The `SKILLS.md` file should be up to date

The `SKILLS.md` file should, at any commit in this repo, contain exactly the full list of the skills.

"The full list" here means that every skill in the repo must be present in `SKILLS.md`, and every skill present in `SKILLS.md` is present in the repo.

## Rule 6: Visualization and topology

The `.ai/VIZ.md` file should, at any commit in this repo, contain exactly the full list of the skills, and a complete list of what skill can invoke what other skill.

"The full list" here means that every skill in the repo must be present in `.ai/VIZ.md`, and every skill present in `.ai/VIZ.md` is present in the repo. Same with invocation relationships: every invocation relationship between two skills must be present in `.ai/VIZ.md`, and every relation that is listed in `.ai/VIZ.md` must be actually present in the repo.

Besides the textual list (two markdown tables, Skills and SkillInvocations), the `.ai/VIZ.md` file should also contain a Mermaid diagram outlining the above graphically: skills as nodes, skill invocation relationships as arrows, where an arrow from A to B means skill A can, under some circumstances, invoke skill B.

## Rule 7: Use of scripts

It is undesirable that skills write temporary Python files to run themselves. If a skill may need to execute a piece of code that is non-trivial, the skill should provide the respective scripts under `.skills/${SkillName}/scripts/`, and the runner should execute the provided scripts rather than improvise equivalent shell or Python on the spot. The mechanical parts of a run — generating identifiers, performing fixed checks, validating and writing run receipts — belong in such scripts; judgment calls stay with the runner.

Scripts are deliberately duplicated rather than shared: when several skills need the same helper, each skill carries its own copy under its own `scripts/` directory. Every skill directory is self-contained, and there is no shared script location in this repository.

Run receipts are a concrete case of this principle: every skill that writes a run receipt must have a dedicated `write-receipt.py` script under `.skills/${SkillName}/scripts/`, and the skill's instructions must direct the runner to call that script with CLI flags — passing `--skill-run-id` and other structured arguments — rather than constructing a JSON object inline (whether via shell `echo`, `python -c`, or any other ad-hoc technique). For aggregate receipts whose content depends on sub-run outcomes, the `write-receipt.py` script must accept sub-run identifiers as flags and read the sub-run receipts itself, so the runner is never asked to extract and re-pass data from those receipts.

## Rule 8: Taste and style

The repo should not contain grammatical errors.

The Markdown texts should be easy to read. The scripts should not be excessive, they should be understandable, they should follow simple input/output formats, they should not perform any surprising operations, and their error message must be short yet complete, and easy to parse by humans and/or other skills.

## Rule 9: Refer to rules by name, not by number

Skills must not refer to the rules in this file by their numbers. The set of rules is expected to stay stable, but their numbering may change as rules are added, removed, or reordered. Whenever a skill needs to reference a rule — in its instructions or in its run receipts — it must use the rule's name (its heading in this file) or a short description of it.

## Rule 10: Hashing and caching of slow checks

Whenever a skill performs a check that is potentially slow or token-consuming — one that requires an agentic runner to read files and exercise judgment — and the outcome of that check is fully determined by a fixed set of files, the skill must use the hashing and caching technique documented in `.ai/CACHING.md`: a provided Python script computes the fingerprint of the check's input set before the check runs, the check is skipped entirely when a cache entry for that fingerprint exists, and a passing verdict writes the cache entry so the next unchanged run is skipped.

The fingerprint must be computed by the skill's provided Python script, never reproduced inline by an agentic runner. The scripts are the single source of truth: because every agent uses the same script, they produce identical fingerprints for identical content, and cache entries are shared across agents and sessions automatically.

Cache entries live under `tmp/caches/`, are written only on passing verdicts, and are never committed. Skills whose own checks are all fast and mechanical are unaffected by this rule, even when they invoke skills that cache.

## Rule 12: Single responsibility per skill

Each skill must have a single, well-defined responsibility. Logically distinct operations — operations that can be independently named, independently cached, independently retried, or independently reasoned about — must not be bundled into the same skill. When a skill handles multiple distinct concerns, each concern must be extracted into its own dedicated skill, and the original skill delegates to the extracted skills via the sub-run mechanism.

Whether two operations are "logically distinct" is determined by whether it is natural to name, invoke, or reason about them independently. For example, checking a single directory invariant and orchestrating the checking of all invariants are two distinct responsibilities, as are performing hygiene checks and performing invariant checks.

## Rule 11: Parallel invocation of spawned skills

When a skill invokes other skills, its definition must state clearly whether those invocations may and should run in parallel.

By default, when a skill starts two or more independent sub-runs — distinct sub-run identifiers, no step depends on another sub-run's receipt — it must instruct the runner to launch them concurrently and to read and aggregate their receipts only after all have completed.

If parallel execution is undesirable, the skill must explain in detail why (for example, a strict ordering requirement, shared mutable state, or each sub-run needing the previous sub-run's receipt).

A skill that invokes exactly one other skill need not include parallelism wording; there is nothing to parallelize.
