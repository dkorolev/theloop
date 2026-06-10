# Skills meta-rules

Every skill in this repository must comply with all of the meta-rules below. The `theloop-internal-validate-skill` skill checks compliance. The `theloop-internal-validate-all-skills` skill checks compliance of all skills.

This file lives at `.theloop/SKILLS-META-RULES.md`, under the `.theloop/` directory in the root of the repo. All file paths in this file are relative to the root of the repo. These meta-rules govern skills in this repository; eventually, the fruits of applying them here will be used to instrument other repositories.

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

Note that the `tmp/` directory is `.gitignore`-d, so skill run receipts are never committed. The `theloop-internal-precommit` skill must check this.

## Rule 4: Universal directory for skills

The skills live under the `.skills/` directory in the root of the repo.

## Rule 5: The `SKILLS.md` file should be up to date

The `SKILLS.md` file should, at any commit in this repo, contain exactly the full list of the skills.

"The full list" here means that every skill in the repo must be present in `SKILLS.md`, and every skill present in `SKILLS.md` is present in the repo.

## Rule 6: Visualization and topology

The `.theloop/VIZ.md` file should, at any commit in this repo, contain exactly the full list of the skills, and a complete list of what skill can invoke what other skill.

"The full list" here means that every skill in the repo must be present in `.theloop/VIZ.md`, and every skill present in `.theloop/VIZ.md` is present in the repo. Same with invocation relationships: every invocation relationship between two skills must be present in `.theloop/VIZ.md`, and every relation that is listed in `.theloop/VIZ.md` must be actually present in the repo.

Besides the textual list (two markdown tables, Skills and SkillInvocations), the `.theloop/VIZ.md` file should also contain a Mermaid diagram outlining the above graphically: skills as nodes, skill invocation relationships as arrows, where an arrow from A to B means skill A can, under some circumstances, invoke skill B.

A skill that invokes one or more other skills must declare those invocations in its `SKILL.md` frontmatter using the `invokes` key — a YAML inline list of skill names (for example, `invokes: [SkillA, SkillB]`). A skill with no invocations omits the key entirely. This structured frontmatter declaration is the sole authoritative source of invocation relationships: the `repo-checks.py` and `mechanical-checks.py` scripts read `invokes` directly from the frontmatter. Parsing free text or natural language for invocation detection is prohibited.

The `invokes:` list must be bidirectionally accurate. Every skill named in `invokes:` must be one that the skill's instruction body actually directs the runner to invoke. Conversely, every skill that the instruction body directs the runner to invoke must appear in `invokes:`. A name listed in `invokes:` that the instructions never actually invoke is a phantom entry and is a violation. A skill invoked by the instructions but absent from `invokes:` is an omission and is equally a violation. The `theloop-internal-validate-skill` runner checks this by reading the skill's instruction body and comparing the set of skills it directs the runner to invoke against the `invokes:` list.

## Rule 7: Use of scripts

It is undesirable that skills write temporary Python files to run themselves. If a skill may need to execute a piece of code that is non-trivial, the skill should provide the respective scripts under `.skills/${SkillName}/scripts/`, and the runner should execute the provided scripts rather than improvise equivalent shell or Python on the spot. The mechanical parts of a run — generating identifiers, performing fixed checks, validating and writing run receipts — belong in such scripts; judgment calls stay with the runner.

Scripts are deliberately duplicated rather than shared: when several skills need the same helper, each skill carries its own copy under its own `scripts/` directory. Every skill directory is self-contained, and there is no shared script location in this repository.

Run receipts are a concrete case of this principle: every skill that writes a run receipt must have a dedicated `write-receipt.py` script under `.skills/${SkillName}/scripts/`, and the skill's instructions must direct the runner to call that script with CLI flags — passing `--skill-run-id` and other structured arguments — rather than constructing a JSON object inline (whether via shell `echo`, `python -c`, or any other ad-hoc technique). For aggregate receipts whose content depends on sub-run outcomes, the `write-receipt.py` script must accept sub-run identifiers as flags and read the sub-run receipts itself, so the runner is never asked to extract and re-pass data from those receipts.

Every Python script provided by a skill must begin with `#!/usr/bin/env python3` as its very first line, and must be committed as executable (mode `+x`). The runner must always invoke such scripts directly by path — for example, `.skills/${SkillName}/scripts/write-receipt.py --flag value` — and must never pass them to an explicit interpreter such as `python` or `python3`. The shebang line ensures the shell selects the correct interpreter automatically.

A skill's `scripts/` directory may also contain **non-entry-point library modules** — Python modules that the skill's own entry-point scripts import (for example, a shared `common.py` holding helpers used by several of the skill's scripts), rather than ones the runner invokes directly. Because the runner never invokes such a module by path, it is exempt from the requirements that it carry a `#!/usr/bin/env python3` shebang, be executable, or be invoked without an interpreter; those requirements bind only the scripts the runner actually runs. Library modules remain skill-local: there is still no shared script location across skills, and the duplication principle above still holds — when several skills need the same library, each carries its own copy under its own `scripts/`.

## Rule 8: Taste and style

The repo should not contain grammatical errors.

The Markdown texts should be easy to read. The scripts should not be excessive, they should be understandable, they should follow simple input/output formats, they should not perform any surprising operations, and their error message must be short yet complete, and easy to parse by humans and/or other skills.

## Rule 9: Refer to rules by name, not by number

Skills must not refer to the rules in this file by their numbers. The set of rules is expected to stay stable, but their numbering may change as rules are added, removed, or reordered. Whenever a skill needs to reference a rule — in its instructions or in its run receipts — it must use the rule's name (its heading in this file) or a short description of it.

## Rule 10: Hashing and caching of slow checks

Whenever a skill performs a check that is potentially slow or token-consuming — one that requires an agentic runner to read files and exercise judgment — and the outcome of that check is fully determined by a fixed set of files, the skill must use the hashing and caching technique documented in `.theloop/CACHING.md`: a provided Python script computes the fingerprint of the check's input set before the check runs, the check is skipped entirely when a cache entry for that fingerprint exists, and a passing verdict writes the cache entry so the next unchanged run is skipped.

The fingerprint must be computed by the skill's provided Python script, never reproduced inline by an agentic runner. The scripts are the single source of truth: because every agent uses the same script, they produce identical fingerprints for identical content, and cache entries are shared across agents and sessions automatically.

Cache entries live under `tmp/caches/`, are written only on passing verdicts, and are never committed. Skills whose own checks are all fast and mechanical are unaffected by this rule, even when they invoke skills that cache.

## Rule 12: Single responsibility per skill

Each skill must have a single, well-defined responsibility. Logically distinct operations — operations that can be independently named, independently cached, independently retried, or independently reasoned about — must not be bundled into the same skill. When a skill handles multiple distinct concerns, each concern must be extracted into its own dedicated skill, and the original skill delegates to the extracted skills via the sub-run mechanism.

Whether two operations are "logically distinct" is determined by whether it is natural to name, invoke, or reason about them independently. For example, checking a single directory rule and orchestrating the checking of all rules are two distinct responsibilities, as are performing hygiene checks and performing rule checks.

## Rule 11: Parallel invocation of spawned skills

When a skill invokes other skills, its definition must state clearly whether those invocations may and should run in parallel.

Prefer the **fan out subagents** phrasing to tell the runner to launch independent sub-runs in parallel — for example, "Fan out subagents — one per rule — to invoke `theloop-internal-check-single-rule`" rather than "launch sub-runs concurrently" or "run in parallel". This vocabulary maps directly to agent runners (such as Cursor) that spawn subagents via a Task tool. Meta-skills that orchestrate multiple sub-runs must use this phrasing in their step instructions and descriptions when parallel execution is intended.

By default, when a skill starts two or more independent sub-runs — distinct sub-run identifiers, no step depends on another sub-run's receipt — it must instruct the runner to fan out subagents (one subagent per sub-run) and to read and aggregate their receipts only after all have completed.

If parallel execution is undesirable, the skill must explain in detail why (for example, a strict ordering requirement, shared mutable state, or each sub-run needing the previous sub-run's receipt).

A skill that invokes exactly one other skill need not include parallelism wording; there is nothing to parallelize.

## Rule 13: Internal skill naming

Skills that take `SkillRunId` as a parameter are orchestration sub-skills: they are invoked by other skills, not typed by humans at a slash-command prompt. Their directory name and `name` frontmatter field must begin with the prefix `theloop-internal-` so they are not suggested when a user types `/` in Claude Code or Cursor.

Skills that do not take `SkillRunId` — including the exceptional skills that generate a `SkillRunId` themselves rather than receiving one from a caller — are the user-facing entry points and must not use the `theloop-internal-` prefix.

The prefix exists because slash-command menus surface skills by name; keeping internal `SkillRunId`-parameterized skills behind `theloop-internal-` leaves discoverable names (`theloop-precommit`, `theloop-buildthis`, and future user-facing skills) uncluttered by sub-skills the user should never invoke directly.

## Rule 14: Commits are authored by the user, never the AI

Any skill that creates a git commit, or that stages changes and directs the user (or runner) to commit them, must ensure the human user is the sole author of the resulting commit. The commit is attributed to the user's configured git identity, and the commit message must contain no AI-assistant attribution of any kind: no `Generated with …` line, no `Co-Authored-By:` trailer naming an AI assistant, model, or tool, and no other mention of the AI that produced the change. A skill that creates or suggests commits must state this requirement explicitly in its instructions.

The `theloop-internal-validate-skill` skill checks this: for every skill whose instructions create a commit or tell the user to commit staged changes, it confirms the skill text explicitly requires the user to be the commit author and explicitly forbids AI-assistant mentions in the commit message. Skills that never create or suggest commits trivially comply and are unaffected by this rule.

## Rule 15: Persistent repository artifacts

Most skills produce only the ephemeral `tmp/${SkillRunId}.json` run receipt (which is `.gitignore`-d) and, in some cases, a commit the user authors. A skill that instead maintains a **durable, committed artifact** in the repository — a directory or file tree it creates and keeps updating across runs — must observe the following, so the artifact stays self-describing, recoverable, and never collides with unrelated repository contents:

- The skill declares, in its body, the single root path of the artifact it owns (for example, a top-level directory), and writes nothing durable outside that root.
- The artifact root carries a machine-readable marker that identifies it as owned by the skill (for example, a `metadata.json` the skill writes on initialization). A skill must refuse to adopt a pre-existing root that lacks its marker: if the root path already exists but the marker is absent, the skill stops and reports that the path belongs to something else rather than writing into it.
- The artifact stays compact: the skill must not emit large collections of per-item files when the same information fits in a bounded set of files. Raw inputs needed only transiently during a run are streamed to the runner, not persisted.
- Any transient files the skill writes under the root while updating it — temporary or lock files — must be `.gitignore`-d so they are never committed, and must be named so that concurrent or interrupted runs cannot collide (see the rule on atomic, idempotent state mutation).

This rule is vacuous for skills that own no durable artifact; they comply trivially.

## Rule 16: Atomic, idempotent state mutation

A skill that mutates **durable on-disk state** — a persistent artifact, as opposed to a write-once run receipt — must do so atomically and idempotently, through a provided script rather than improvised inline edits:

- Every mutation is **atomic**: the script writes the new content to a temporary file and renames it over the target in a single atomic step, so neither a reader nor a crash ever observes a partially written file. The temporary file is named with the `SkillRunId` as its nonce, so an interrupted run leaves attributable, sweepable debris and concurrent runs never share a temporary name.
- Every mutation is **idempotent and convergent**: re-running the same logical operation, or running two operations concurrently, leaves the state correct without accumulating duplicates or spuriously rewriting unchanged content. A mutation whose computed result equals the current state is a no-op.
- Every mutation **guards against lost updates**: a concurrent writer's changes are not silently clobbered — for instance, by an optimistic compare-and-swap that commits the rename only when the target is unchanged since it was read, retrying after a randomized backoff otherwise.

The specific mechanism (optimistic concurrency, a version field, and so on) and its parameters are the skill's own choice and belong in the skill, not in this file; this rule fixes only the contract: atomic, idempotent, lost-update-resistant, performed by a script.

Do not reach for a blocking lock such as `flock` to make a mutation airtight. Skills here are driven by an agentic, English-prompt runner, so every gate is **probabilistic by nature**: a step may stall, retry, be interrupted, or never resume. A blocking lock held by such a runner can therefore **deadlock** — the holder may hang and never release it — which is exactly the unbounded wait the rule on time-bounded operations forbids. We deliberately prefer the small, self-healing chance of a lost update from lock-free optimistic concurrency over the risk of a deadlock from a held lock: a bounded optimistic retry has a bounded worst case, a blocking lock does not. Because the gates are probabilistic anyway, an occasional lost update is an acceptable, recoverable outcome; a deadlock is not.

## Rule 17: Time-bounded operations — no unbounded waits

No skill may wait on anything indefinitely. Every operation a skill awaits — a spawned sub-run (subagent), an invoked script, or an external command such as `gh` or `git` — must be time-bounded by the party that awaits it, and must end in one of exactly two ways: it completes, or it is terminated and reported as a **timeout error**. It is never left hanging.

- The bound is set by the caller — the party that awaits. When it elapses, the awaited operation is treated exactly as any other failure: it yields a structured error (an `{"error": "timeout: …"}` receipt for a sub-run, or a short `timeout:` message on stderr for a script), so the caller can retry, skip, or fail — but always proceeds rather than blocking.

- For fan-out this composes with the rule on parallel invocation of spawned skills: a parent that aggregates sub-run receipts must bound each sub-run, and if a sub-run has not completed when its bound elapses, the parent treats that sub-run as a timeout error — *including* the case where the timed-out sub-run never wrote its `tmp/<SkillRunId>.json` receipt. A receipt still absent once the bound has elapsed is a timeout, not a reason to keep waiting.

- A script that makes a blocking call — a network request, a subprocess, or any wait on an external resource — must impose its own timeout and exit with a short timeout error rather than blocking forever; it must never await an external resource without a bound.

The effect is that a single slow, stuck, or dead operation can never stall an entire run: the worst case for any wait is a bounded delay followed by a clean, reported timeout that the rest of the run can act on. This is also why a hang-prone lock is the wrong tool for the rule on atomic, idempotent state mutation: an optimistic retry has a bounded worst case, whereas a blocking lock held by a hung process does not.

## Rule 18: Split slow work into collect-then-analyze, and cache the collection

When a unit of work is slow — a network fetch, or any expensive gathering — prefer to split it into two steps: first **collect** the data, then **analyze** it. The collection step writes its result for each input to a file named cleanly by that input's own identity (for example, the pull-request number), through a temporary file and an atomic rename, so that the file's existence is itself the proof that the input was fully collected. A later step — or a later run after an interruption — reuses that file instead of redoing the slow collection.

- Such a cache is a reproducible convenience, not part of the committed journal: keep it in a gitignored location — for instance under the artifact root, whose transient files the rule on persistent repository artifacts already requires to be gitignored — so it never bloats what is committed.
- Mark an input as fully processed only after every durable effect of processing it has been committed, and key each journaled output by a stable identity so that re-processing refines the existing entry rather than appending a second one — reconciling against the existing journal when that key comes from a judgment rather than mechanically from the input.
- Together these give crash-safe resumption: after an interruption the run picks up where it stopped, re-processing only the inputs whose completion was not yet recorded — at worst repeating cheap analysis, never repeating the slow collection, never losing an input, and never journaling one more than once.

This rule is vacuous for skills whose work is neither slow nor journaled from a stream of inputs.
