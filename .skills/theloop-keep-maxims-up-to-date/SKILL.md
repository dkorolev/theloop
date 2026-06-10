---
name: theloop-keep-maxims-up-to-date
description: Distills a repository's unwritten engineering paradigms — its maxims — from merged pull-request history into per-topic files under maxims/. Takes no parameters and generates its own SkillRunId; initializes and inventories existing conventions, fetches batches of merged PRs, judges each for genuine paradigms not already covered, and records them with evidence links — atomically and idempotently.
---

# theloop-keep-maxims-up-to-date

This skill distills the **maxims** of a repository — the unwritten engineering
paradigms the team actually converged on — from its **merged pull-request history**,
and writes them into per-topic files under a top-level `maxims/` directory. A maxim
is a paradigm that is *not already captured* by an existing convention file or design
doc. All deterministic work (creating the directory, reading and writing
`metadata.json`, fetching PRs, rendering and upserting maxim entries) is done by the
bundled scripts; your only job is the judgment those scripts cannot do — deciding
which patterns are genuine paradigms, which existing convention already covers them,
and how to phrase them — fed back to the scripts as small JSON records.

Per the rule on run receipts, this is one of the exceptional skills that does not take the `SkillRunId` parameter — it is invoked directly by a human, where a caller-supplied identifier would serve no purpose. It generates a fresh `SkillRunId`
of its own and writes its own run receipt.

Running this skill is an operation fully contained within the directory of this
repository: do not read, write, or otherwise access any file outside the repository.
The one outward action is querying GitHub through the `gh` CLI to read this
repository's own pull requests.

## The durable artifact this skill owns

Per the rule on persistent repository artifacts, this skill owns exactly one durable,
committed artifact: the top-level **`maxims/`** directory. Its `metadata.json` is the
ownership marker. The skill keeps the *committed* journal compact — `metadata.json`
plus, per category, a `.yml` **source of truth** and a `.md` **generated** from it (no
per-maxim markers); no per-PR files are committed.
Collected PR data is cached under the gitignored `maxims/cache/<pr>.json` for reuse
across runs (per the rule on splitting slow work) and is never committed. The skill
**refuses to adopt a `maxims/` it did not create**: if `maxims/` exists but has no
`metadata.json`, every script stops and
reports that the path belongs to something else. All updates to the artifact go
through the bundled scripts, which write atomically and idempotently per the rule on
atomic, idempotent state mutation; you must never hand-edit files under `maxims/`.

## Parameters

This skill takes no parameters. If any parameters are passed, stop immediately and
report an error.

## Steps

The Python scripts under `.skills/theloop-keep-maxims-up-to-date/scripts/` are
executable and begin with `#!/usr/bin/env python3`; run each one directly by path —
never prefix it with `python` or `python3`. `common.py` in that directory is a
library the other scripts import; you never invoke it directly. Pass the generated
`SkillRunId` to every script that takes `--run-id`.

1. **Check the configuration gate, then generate the run identifier.** First run
   `.skills/theloop-keep-maxims-up-to-date/scripts/check-configured.py` from the
   repository root. If it exits non-zero (the repository has been theloopified but
   `newrepo-theloopify-internal-postinit` has not completed), stop immediately: tell
   the user they must run `newrepo-theloopify-internal-postinit` first, and do not
   generate an identifier. When it reports configured — including the not-applicable
   case in a non-theloopified repository, such as the theloop repository itself —
   continue. Then run `.skills/theloop-keep-maxims-up-to-date/scripts/new-run-id.sh`
   from the repository root: it prints a fresh `SkillRunId` in the default format
   codified in the rule on run receipts, `YYYYMMDD-HHMMSS-{six_random_latin_lowercase_characters}`.
   Tell the user which identifier was generated. Then confirm that
   `tmp/<SkillRunId>.json` does not already exist; if it does, stop immediately and
   report an error without touching the file. **You will write `tmp/<SkillRunId>.json`
   as the run receipt when this skill completes — on success or error alike.**

2. **Initialize, inventory, and verify consistency.** Run
   `.skills/theloop-keep-maxims-up-to-date/scripts/init-maxims.py --run-id <SkillRunId>`.
   It creates `maxims/` when absent (or reconciles it when present) and prints, under
   `read_these`, the convention files the repository already has. **Read each of those
   files** — they are the *already-covered* set: when a candidate maxim is already
   stated there, link to it instead of recording it.

   Then run `.skills/theloop-keep-maxims-up-to-date/scripts/check-maxims.py`. The
   `.yml` files under `maxims/` are the single source of truth; each `.md` is generated
   from its `.yml`. This verifies a one-to-one `.yml`↔`.md` mapping, that every category
   listed in `metadata.json` is present, and that each `.md` is exactly what its `.yml`
   generates. **If it reports any discrepancy, STOP** — do not collect, judge, or record
   anything. Write the run receipt with `"status": "error"` and tell the user to
   harmonize first: the `.yml` is the source of truth, so decide which side holds the
   latest intended content (if they were editing a `.md` directly, fold those newest
   edits back into its `.yml`), then regenerate each `.md` with
   `.skills/theloop-keep-maxims-up-to-date/scripts/render-maxims.py maxims/<CATEGORY>.yml`
   (it prints the generated `.md` to stdout) and iterate until `check-maxims.py` reports
   `pass`. Offer to perform this harmonization for them.

3. **Collect a batch of merged PRs.** This skill processes the **entire** merged-PR
   history — steps 3–5 form a loop you repeat until none remain (see step 5); the batch
   is only the unit of in-context judgment, never a coverage cap. Run
   `.skills/theloop-keep-maxims-up-to-date/scripts/fetch-prs.py --run-id <SkillRunId> --limit N`
   with a batch size `N` (10–25 is reasonable: large enough to make steady progress,
   small enough to judge in one context). This is the slow, collect-half of the work
   (per the rule on splitting slow work): it verifies `gh` access, lists merged-only
   PRs not yet considered, and for each gathers its commits, reworked-files signal,
   reviews, and comments. Each fully-collected PR is cached atomically to the gitignored
   `maxims/cache/<pr>.json` and reused instead of being re-fetched, so an interrupted
   run resumes without repeating the slow fetch. The digest is printed to stdout (the
   cache is gitignored, never part of the committed journal). If it exits with an
   error — `gh` not installed, not authenticated, or a `gh` call timed out (every `gh`
   call is time-bounded, per the rule on time-bounded operations) — write the run
   receipt with `"status": "error"` and stop, reporting the message. When
   `fetched_count` is `0`, every merged PR has been considered: skip to step 6.

4. **Judge each PR.** This is the only genuine judgment step. Read
   `.skills/theloop-keep-maxims-up-to-date/references/maxim-format.md` and apply it:
   read the whole batch digest first so repetition across the batch is visible, then
   judge each PR into exactly one of four outcomes (record a new maxim; skip as
   already-covered and link it; refine an existing maxim; or nothing). Start from each
   PR's `reworked_files` and any CHANGES_REQUESTED reviews. Bias toward precision over
   recall.

5. **Record, then consider — in that order.** Per the rule on splitting slow work,
   order these so an interruption can never lose or double-record. For each maxim you
   decided to record, pipe its JSON (an object, or a list of objects for several
   maxims from one PR) to
   `.skills/theloop-keep-maxims-up-to-date/scripts/record-maxim.py --run-id <SkillRunId>`.
   It updates the category's `.yml` source of truth first and immediately regenerates
   the `.md` from it. Re-recording upserts by the maxim's stable title-derived id, so
   reconcile against the existing maxims (the category `.md` files) — a re-judged PR
   must refine its existing maxim, not create a near-duplicate. **Only after a PR's maxims are durably
   recorded** (record-maxim.py reported success) run
   `.skills/theloop-keep-maxims-up-to-date/scripts/consider-pr.py --run-id <SkillRunId> --pr <numbers>`
   for that PR — and for every PR that produced no maxim. If record-maxim.py errors
   for a PR, do **not** consider that PR: leave it unconsidered so it is re-judged later
   (reusing its cache, no re-fetch). **Then loop: return to step 3 for the next batch
   and keep going until a fetch reports `fetched_count` `0`. This is mandatory — the run
   is not complete until every merged PR has been considered. Do not stop after one
   batch, and do not declare success while any merged PR remains unconsidered.**

6. **Surface any human-gated changes.** Two kinds of change reverse or restructure
   durable judgments, so this skill **proposes them but does not perform them**
   without explicit human confirmation: reversing a maxim (marking it
   `superseded` or removing it because newer PRs contradict it) and splitting or
   moving a category whose file has grown to mix unrelated concerns. If you see cause
   for either, describe the proposed change and its evidence to the user and wait for
   explicit confirmation before recording it. Default to adding to existing files;
   never reorganize silently.

7. **Report, and hand off for commit.** Tell the user: that the **entire merged-PR
   history was processed** — the total number of PRs now in the considered set, and a
   confirmation that the final fetch returned `fetched_count` `0` so none remain
   unprocessed; the conventions you linked (not re-derived); the maxims added or refined
   and their category files; evidence highlights (commit pairs, named reviewers); and
   any human-gated proposals awaiting their decision. The `maxims/` artifact is a normal
   repository artifact: leave it for the user to review and commit. Per the rule that
   commits are authored by the user, do not create the commit on their behalf, and any
   commit of `maxims/` must be authored by the user with no AI-assistant attribution
   of any kind in the message.

8. **Write the run receipt** by calling
   `.skills/theloop-keep-maxims-up-to-date/scripts/write-receipt.py` with CLI flags:
   `--skill-run-id` and `--status pass|error`; when status is `pass`:
   `--prs-considered N`, `--maxims-written N` (created plus refined this run),
   `--categories-touched "a,b"` (comma-separated category ids, empty string for none),
   and `--human-decisions-requested N`; when status is `error`: `--error TEXT`. The
   script validates the schema and refuses to overwrite an existing receipt.

## Run receipt schema

The JSON object written to `tmp/<SkillRunId>.json` must have exactly these fields:

```json
{
  "skill_run_id": "string — the generated SkillRunId",
  "skill": "theloop-keep-maxims-up-to-date",
  "status": "pass | error",
  "prs_considered": "integer|null — PRs added to the considered set this run, null when error",
  "maxims_written": "integer|null — maxims created or refined this run, null when error",
  "categories_touched": "array of strings|null — category ids written to, null when error",
  "human_decisions_requested": "integer|null — reversal/split proposals surfaced, null when error",
  "error": "string|null — set only when status is error"
}
```

- `status` is `"pass"` when the run completed — even when it produced no maxims —
  with `error` `null`;
- `"error"` when the skill could not proceed at all (unexpected parameters, a
  pre-existing receipt, `gh` unavailable, or a `maxims/` that belongs to something
  else), with the count fields `null` and `error` explaining why.

**Run receipt (final reminder):** before finishing this skill — on success or error
alike — write `tmp/<SkillRunId>.json` containing a single well-formed JSON object
conforming to the schema above, via the `write-receipt.py` script. The only exception
is when the run was aborted because `tmp/<SkillRunId>.json` already existed before the
run: in that case, never overwrite it.
