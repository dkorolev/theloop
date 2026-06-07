# Directory Invariants

This file lives at `.ai/INVARIANTS.md`, under the `.ai/` directory in the root of the repo. All file paths in this file are relative to the root of the repo.

A **directory invariant** is any file whose name ends with `-INVARIANT.md`, placed in any directory of this repository. It states a rule in plain English that must hold for the contents of that directory. Checking an invariant means an agentic runner reads the rule and judges the directory against it — the rule is prose, not a script, which is why it can express requirements that scripts cannot.

## Scope

An invariant covers its directory **fully recursively**: every non-gitignored file under the invariant's directory, at any depth, is in scope. A nested directory may carry its own invariant file; the inner invariant is an independent, additional check over its own subtree and does not shrink the outer invariant's scope.

Every invariant is checked from within its own directory, over its own subtree, and nothing else.

## The registry: `ai-invariants.yml`

The file `ai-invariants.yml` at the root of the repository lists the paths of all invariant files, as a flat YAML list:

```yaml
- .ai/STYLE-INVARIANT.md
- some/other/directory/NAMING-INVARIANT.md
```

The registry exists so that no run ever has to crawl the repository looking for invariants. It must match the repository exactly, in both directions: every non-gitignored `*-INVARIANT.md` file is listed, and every listed path exists. When the repository contains no invariants, the registry is an empty list (`[]`). This exactness is checked mechanically by the pre-commit gate.

## When invariants run

Invariants are checked by `PreCommitSkillWithRunId` as part of the pre-commit gate. To keep model usage minimal, each invariant is cached using the technique documented in [`.ai/CACHING.md`](CACHING.md):

* the invariant's input set is its directory subtree (which includes the invariant file itself, so editing the rule invalidates the cache);
* the check name is `invariant:<path-to-INVARIANT.md>`, so the invariant's identity is part of the fingerprint;
* the probe step runs first — a single Python script call that classifies every invariant as **cached** (pass already on record for byte-identical content) or **stale** (must run);
* cached invariants are skipped entirely; stale invariants are run concurrently, since they are independent of each other;
* on a cache miss the runner reads the invariant file, judges the subtree against the rule it states, and writes the cache entry only when the invariant passes.

A failing invariant blocks the commit, and its failure is never cached.

## Writing an invariant

Keep the rule short, concrete, and judgeable from the directory's contents alone. An invariant that needs information from outside its own subtree is mis-scoped: move it up to the directory that contains everything it needs.
