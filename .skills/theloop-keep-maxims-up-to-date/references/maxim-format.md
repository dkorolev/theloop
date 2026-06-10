# What counts as a maxim, and how to record one

A **maxim** is an unwritten engineering paradigm the team actually converged on,
distilled from merged pull-request history, that is **not already captured** by an
existing convention file (CONTRIBUTING, CLAUDE.md/AGENTS.md/cursor rules, style
guides, linter configs) or design doc. If `init-maxims.py` listed a file under
`read_these`, read it: anything it already states is *covered* — link to it, do not
re-derive it as a maxim.

## The three signals, strongest first

1. **Rework inside a PR.** Something done one way in an early commit and redone in a
   later one. The *final* approach is the maxim; the commit pair `[before, after]`
   is the evidence. `fetch-prs.py` surfaces this as `reworked_files` (files touched
   in more than one commit). When `reworked_files` is `null` — a single-commit PR,
   typically from squash-merge — this signal is simply absent; do not infer it.
   Maxims mining works best on repositories that **do not squash-merge**; when they
   do, lean on the other two signals.
2. **Reviewer steering.** A review comment or a CHANGES_REQUESTED review pushing the
   author toward a norm. Attribute it to the reviewer by login. This is the most
   durable signal and survives any merge strategy.
3. **Repetition across PRs.** The same correction recurring across PRs promotes a
   maxim from `proposed` to `confirmed`.

## The four outcomes — every PR ends in one

Read the **whole batch digest first** so repetition across the batch is visible,
then judge each PR. Exactly one outcome per PR, and **every** PR is then passed to
`consider-pr.py` so it is never re-fetched:

1. **Genuine new paradigm, not covered** → record it, then consider the PR.
2. **Already covered** by a convention or design doc → do *not* record; note the
   covering file; consider the PR.
3. **Refinement or repeat** of an existing maxim → record it again with the full,
   cumulative record (re-passing prior evidence), bumping `proposed`→`confirmed`
   when warranted; consider the PR.
4. **Noise / nothing** → record nothing; consider the PR.

Bias toward **precision over recall**: when evidence is ambiguous (a one-off bugfix,
not a paradigm), record nothing and just consider the PR. A short, sharp `maxims/`
is worth more than a long, hedged one.

## The maxim record (what you pipe to `record-maxim.py`)

`record-maxim.py` writes this into the category's **`.yml` source of truth** (upsert by
id) and then regenerates the category's **`.md`** from it. You never edit the `.yml` or
`.md` by hand here — you pass JSON, and the script owns both files.

```json
{
  "category": "frontend",
  "title": "Colocate component styles",
  "statement": "Keep a component's styles in the same folder as the component.",
  "rationale": "Reviewers moved styles back next to components across PRs.",
  "applies_to": ["src/components/**"],
  "status": "confirmed",
  "evidence": [
    {"pr": 123, "commit_pair": ["a1b2c3d", "d4e5f6a"], "comment_by": "alice",
     "note": "asked to move styles back next to the component"},
    {"pr": 130, "comment_by": "carol"}
  ]
}
```

- `title` is the stable identity. The id is derived from the **title alone**
  (`slug(title)`), independent of category — so keep the title short and stable, and
  a later category move never breaks the id or its evidence links. Re-recording the
  same title **refines in place**; it does not duplicate.
- `category` is a lowercase-kebab id (`frontend`, `data-flow`, `sql-patterns`). It maps
  to two files: the UPPERCASE-with-hyphens `.yml` source of truth and its generated
  `.md` (`FRONTEND.yml` + `FRONTEND.md`, `DATA-FLOW.yml` + `DATA-FLOW.md`). A category
  that does not exist yet is created on demand — the taxonomy is open.
- `status`: `proposed` (single-PR observation) or `confirmed` (repeated, or
  explicitly enforced by a CHANGES_REQUESTED review). `superseded` exists too, but
  see the human gate below.
- `commit_pair`: `[before, after]` for the rework signal; omit when absent.
- `evidence` may list several PRs; pass the **full** list each time you refine, since
  the maxim's entry is regenerated from exactly what you pass.
- Pass a **JSON list** to record several maxims from one PR in a single call.

## Two changes that require asking the human first

These reverse or restructure durable judgments, so the skill **proposes but does not
act** — surface the proposal and wait for explicit human confirmation:

- **Reversing a maxim** (`status: "superseded"`, or removing it) because newer PRs
  contradict it. Recording a fresh `proposed`/`confirmed` maxim is *not* a reversal
  and needs no gate; only contradicting or retiring an existing one does.
- **Splitting or moving a category** when a file has grown to mix clearly unrelated
  concerns. Default to adding to existing files; never reorganize silently. Because
  the maxim id is category-independent, a move only relocates the maxim's entry from
  one category `.yml` to another (regenerating both `.md` files) and updates its
  `category` field — but it is still a human-gated decision.
