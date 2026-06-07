# Directory Rules

This file lives at `.ai/RULE-FILES.md`, under the `.ai/` directory in the root of the repo. All file paths in this file are relative to the root of the repo.

A **directory rule** is any file whose name ends with `-rule.yml`, placed in any directory of this repository. It states a rule in plain English that must hold for a scoped subset of that directory's contents. Checking a rule means an agentic runner parses the YAML, resolves which files are in scope, reads the `rule:` text, and judges those files against it.

## Rule file schema

Each `*-rule.yml` file is a YAML mapping with:

* **`rule`** (required) — a non-empty string: the prose rule to judge.
* **`use`** (optional) — a list of paths, relative to the directory containing the rule file. Each entry names a file or a directory; a directory entry expands to every non-gitignored file under it recursively. When present, only the listed paths (plus the rule file itself) are in scope.
* **`exclude`** (optional) — a list of paths with the same shape as `use`. When present, every non-gitignored file under the rule file's directory is in scope except the rule file itself and anything matched by the list.

`use` and `exclude` are mutually exclusive. When neither is present, the scope is the entire directory subtree: every non-gitignored file under the rule file's directory, recursively.

Path entries must stay within the rule file's directory (`../` escapes are rejected). A path that does not exist is a schema error reported before any agentic judgment runs.

## Scope

A rule covers its directory. Nested directories may carry their own `*-rule.yml`; each is an independent check over its own resolved scope and does not shrink an outer rule's scope.

Every rule is checked from within its own directory, over its resolved scope only.

## The registry: `ai-rules.yml`

The file `ai-rules.yml` at the root of the repository lists the paths of all rule files, as a flat YAML list:

```yaml
- example/math/add/add-rule.yml
```

The registry exists so that no run ever has to crawl the repository looking for rules. It must match the repository exactly, in both directions: every non-gitignored `*-rule.yml` file is listed, and every listed path exists. When the repository contains no rules, the registry is an empty list (`[]`). This exactness is checked mechanically by the pre-commit gate.

## When rules run

Rules are checked by `InternalSkillCheckAllRulesWithRunId`, which is invoked by `InternalSkillPreCommitSkillWithRunId` as part of the pre-commit gate. Individual rules are each checked by `InternalSkillCheckSingleRuleWithRunId`. To keep model usage minimal, each rule check is cached using the technique documented in [`.ai/CACHING.md`](CACHING.md):

* the rule's input set is its resolved scope (the rule file plus every in-scope file; editing the rule text or scope invalidates the cache);
* the check name is `rule:<path-to-rule.yml>`, so the rule's identity is part of the fingerprint;
* `InternalSkillCheckSingleRuleWithRunId` parses and validates the YAML first — invalid syntax or schema fails mechanically with a precise error;
* then it probes the cache — a single Python script call that classifies the rule as **cached** (pass already on record for byte-identical content) or **stale** (must run);
* cached rules are skipped entirely; stale rules are run concurrently by `InternalSkillCheckAllRulesWithRunId`, since they are independent of each other;
* on a cache miss `InternalSkillCheckSingleRuleWithRunId` reads the `rule:` text and judges only the scoped files, then writes the cache entry only when the rule passes.

A failing rule blocks the commit, and its failure is never cached.

## Writing a rule

Keep the `rule:` text short, concrete, and judgeable from the scoped files alone. A rule that needs information from outside its scope is mis-scoped: move it up to the directory that contains everything it needs, or narrow or widen scope with `use` / `exclude`.
