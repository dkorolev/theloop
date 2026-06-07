# Hashing and Caching of Slow Checks

This file lives at `.ai/CACHING.md`, under the `.ai/` directory in the root of the repo. All file paths in this file are relative to the root of the repo, and all hashing and caching operations are performed from the root of the repo.

Some checks in this repository are slow or token-consuming: they require an agentic runner to read files and exercise judgment. Re-running such a check when nothing it reads has changed is pure waste. This document defines the one technique every such check uses to skip redundant runs: a content fingerprint of the check's inputs, and a cache of passing verdicts keyed by that fingerprint.

## The input set

Every cached check declares its **input set**: the files whose contents fully determine the check's outcome. An input set consists of:

* a **directory subtree** — every file under a given directory, recursively, that is not gitignored; both tracked files and untracked-but-not-ignored files count, so the enumeration is `git ls-files --cached --others --exclude-standard -- <directory>`, filtered to files that exist in the working tree;
* optionally, **extra files** outside that directory that the check also reads (for example, a check of one skill also reads `.ai/RULES.md`, `SKILLS.md`, and `.ai/VIZ.md`).

A check whose outcome is not fully determined by a fixed set of files cannot be cached with this technique and must not pretend otherwise.

## The fingerprint

The fingerprint is computed by a provided Python script, never by an agentic runner. This is the key design constraint: because every cached check ships a dedicated script that performs exactly the same computation, any two agents running the same script on the same files arrive at the same fingerprint and therefore see the same cache entry. An entry written by one agent is valid for every other agent, and a pass recorded in one working session is honored in the next without re-running the check. No agent should reimplement the fingerprint computation inline — doing so risks silent divergence and defeats the sharing property.

1. Enumerate the input set as described above.
2. Sort the paths lexicographically (plain byte order of the path strings, relative to the repository root).
3. Compute the SHA-256 of the contents of every file in the input set.
4. Build the **manifest**: one `check:` line naming the check, followed by one line per file, in sorted order:

   ```
   check: <check name>
   <sha256-of-file>  <path>
   <sha256-of-file>  <path>
   ```

   Every line, including the last, is newline-terminated. The check name is part of the manifest by design: two different checks over identical content must never share a cache entry.
5. The **fingerprint** is the SHA-256 of the manifest, encoded as UTF-8.

## The cache

Cache entries live under `tmp/caches/`. The `tmp/` directory is gitignored, so the cache is local to one working copy and is never committed; deleting `tmp/caches/` is always safe and merely forces fresh runs.

A cache entry is the file `tmp/caches/<fingerprint>.txt`. It is written **only when the check passes**, and it is written by a script, never free-form. Its content is human-readable on purpose — open it to see exactly what was checked and what was hashed:

```
check: <check name>
verdict: pass
files:
<sha256-of-file>  <path>
<sha256-of-file>  <path>
```

Failures are never cached: a failing check leaves no entry and runs again next time.

## The protocol

Before running a cached check, the runner executes the check's probe script, which computes the fingerprint and looks for `tmp/caches/<fingerprint>.txt`:

* **Cache hit** — the entry exists: the exact same check has already passed over byte-identical inputs. The check is skipped entirely — the runner does not read the inputs, does not re-judge anything, and reports the check as passed with a note that the verdict comes from the cache.
* **Cache miss** — no entry: the runner performs the check for real. If it passes, the runner executes the check's write script, which recomputes the fingerprint and writes the entry. If it fails, nothing is written.

Because the input set includes the file that states the rule being checked (a skill's `SKILL.md`, a gate's `GATE.md`), editing the rule text invalidates the cache automatically, exactly as it should.

## Who uses this

* The rule on hashing and caching of slow checks in [`RULES.md`](RULES.md) requires every skill with slow or token-consuming, content-determined checks to use this technique.
* `ValidateSkill` caches its verdict per skill: the input set is the skill's directory subtree plus `.ai/RULES.md`, `SKILLS.md`, and `.ai/VIZ.md`, under the check name `ValidateSkill:<SkillName>`.
* `PreCommitSkillWithRunId` caches every directory rule, as described in [`.ai/RULE-FILES.md`](RULE-FILES.md): the input set is the rule's resolved scope (the rule file plus every in-scope file), under the check name `rule:<path-to-rule.yml>`.

The scripts that implement the technique are deliberately duplicated per skill, under each skill's own `scripts/` directory, per the rule on use of scripts. An agentic runner must call the provided scripts rather than reproduce the fingerprint algorithm in ad-hoc shell or Python — only the scripts are authoritative.
