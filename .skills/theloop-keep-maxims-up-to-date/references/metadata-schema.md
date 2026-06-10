# The `maxims/` artifact and its `metadata.json`

The skill owns exactly one durable, committed artifact: the top-level `maxims/`
directory. The committed files are `maxims/metadata.json` and, per category, a `.yml`
**source of truth** and a `.md` **generated** from it — there are **no committed per-PR
files** and **no per-maxim markers**. Each maxim's distilled references live in its
`.yml` evidence; the full PR digest is streamed to stdout for in-context judgment.

Slow collection is split from analysis (per the rule on splitting slow work):
`fetch-prs.py` caches each fully-collected PR to `maxims/cache/<pr>.json` — written
via temp file + atomic rename, its existence the proof of full collection — and reuses
it on a later run instead of re-fetching. The `cache/` directory is **gitignored**:
it is a reproducible convenience, never part of the committed journal, and safe to
delete.

```
maxims/
├── metadata.json        # ownership marker + conventions + categories + considered PRs
├── .gitignore           # ignores cache/, *.tmp, *.lock
├── FRONTEND.yml         # source of truth for a category's maxims
├── FRONTEND.md          # generated from FRONTEND.yml — never hand-edited
├── <NEW-CATEGORY>.yml   # created on demand, alongside its generated .md
└── cache/<pr>.json      # gitignored: collected PR data, reused across runs
```

## `metadata.json` layout

| Key | Meaning |
|---|---|
| `generator_version` | Version of the generator that wrote this file, as `YYYYMMDD`. |
| `existing_conventions` | A flat array of convention file paths already in the repo — linked, not re-derived. |
| `categories` | A flat array of the category `.yml` file names present (e.g. `["FRONTEND.yml", …]`); every one listed **must** exist. |
| `analyzed_prs` | A **sorted array of PR numbers**: the considered-set dedup guard. |

The maxims themselves are **not** indexed in `metadata.json` — the `.yml` files are
their source of truth. A maxim's `id` is `slug(title)`, category-independent, so a
category move never changes it. A category id maps to `UPPERCASE.yml` + `UPPERCASE.md`
with hyphens kept (`data-flow` → `DATA-FLOW.yml` + `DATA-FLOW.md`).

## Two dedup mechanisms

- **`analyzed_prs`** prevents reprocessing a PR: a PR listed there is never fetched
  or judged again. `consider-pr.py` inserts into it.
- **The maxim `id`** makes `record-maxim.py` **upsert** the maxim in its category
  `.yml` (then regenerate the `.md`), so re-recording refines a maxim in place rather
  than duplicating it — no markers involved.

## The `.yml` source of truth and the generated `.md`

Each category is a `.yml` (source of truth) and a `.md` generated from it by
`render-maxims.py`, which prints the `.md` for a given `.yml` to stdout. `record-maxim.py`
always updates the `.yml` first, then regenerates the `.md`. At the start of every run,
`check-maxims.py` enforces that the two agree: a one-to-one `.yml`↔`.md` mapping, every
`categories` entry present, and each `.md` byte-identical to its rendered `.yml`. On any
discrepancy the skill stops and asks the human to harmonize — regenerate the `.md` from
the `.yml`, taking the newest intended content first — before doing anything else.

## How writes stay consistent (the contract scripts enforce)

Every durable mutation goes through `common.py`, never an inline edit, and obeys the
rule on atomic, idempotent state mutation:

- **Atomic.** Write to `maxims/<file>.<SkillRunId>.tmp`, `fsync`, then `os.replace`
  over the target — a reader (or a crash) never sees a half-written file. The
  `SkillRunId` nonce makes interrupted-run debris attributable and sweepable, and
  keeps concurrent writers from sharing a temp name. The `.tmp`/`.lock` siblings are
  gitignored, so they are never committed.
- **Lost-update-resistant (optimistic, lock-free).** `cas_update` captures the
  target's `(mtime_ns, size)` when read and commits the rename only if that is
  unchanged; otherwise it deletes its temp and retries after a randomized
  exponential backoff (~20 ms base, ~1.4× growth) — no lock files, no stale locks.
  The runner invokes these scripts sequentially, so genuinely concurrent writers do
  not arise in normal operation; and because `analyzed_prs` is the dedup guard, a
  considered-insert lost to an extreme concurrent race is simply re-surfaced and
  reconsidered on the next run. The artifact never corrupts — `os.replace` always
  leaves a reader a whole file.
- **Idempotent / convergent.** A mutation whose result equals the current state is a
  no-op (nothing is rewritten). Re-running a batch therefore converges: considering
  an already-considered PR, or recording an unchanged maxim, changes nothing.

## Initialization and the ownership guard

`init-maxims.py` is the **sole** creator of `maxims/`. It writes `metadata.json`
create-exclusive (never clobbering an analyzed PR or a recorded maxim) and, on
re-run, only reconciles the convention inventory. Because `maxims/` is a
common directory name, every script treats **"`maxims/` exists but has no
`metadata.json`"** as *not mine — stop and report*, never as "uninitialized, go
ahead." This is the persistent-artifact ownership marker in action.
