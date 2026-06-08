# theloopify and the client-repo skill bundle

## Summary

`theloopify` is a root-level shell script that instruments a freshly cloned **client repository** with the theloop agent workflow — the *discuss → issue → implement → PR* loop — without dragging in theloop's own maintenance machinery. It copies a curated bundle of skills into the client's `.theloop/skills/` (canonical real files), symlinks them into every supported coding-agent skills directory (`.cursor/`, `.claude/`, `.codex/`, `.agents/`), rewrites `.skills/` path references to `.theloop/skills/`, and writes the `.theloop/` scaffolding that governs the rest of the workflow. The mechanical install stops there; a one-time **agentic** `theloop-post-setuprepo` step then reads the client's docs, test tooling, and CI gates and authors a free-form `PRECOMMIT.md`. Two invariants hold the design together: **one feature per fresh clone** (`theloopify` runs once and the tree is then dedicated to a single feature), and **feature PRs contain only user code** (theloop scaffolding is hard-excluded at commit time via `.theloop/do_not_commit.txt`).

## Rationale

theloop's skills today only work inside the theloop repo itself, because they lean on repo-wide meta machinery: `InternalSkillValidateAllSkills`, `InternalSkillCheckAllRulesWithRunId`, the `ai-rules.yml` registry, `SKILLS.md`, and `.theloop/VIZ.md`. A user who wants the workflow in *their* repo needs the slim user-facing path — capture an issue, implement it, gate it, open a PR — and nothing else. The design therefore draws a hard line between:

- **Mechanical vs. agentic.** `theloopify` is a deterministic shell script (safe to read, predictable, re-runnable in principle). Anything that requires understanding the target repo — above all, what its pre-commit checks should be — is deferred to the agentic `theloop-post-setuprepo`. Forcing `PRECOMMIT.md` generation into the shell would be brittle and wrong.
- **Copied vs. symlinked-to-theloop.** Skills are *copied* into the client (self-contained, portable) rather than symlinked back to the theloop checkout, so the client keeps working after the theloop checkout moves or disappears. Within the client, the four agent directories *symlink* to a single canonical copy under `.theloop/skills/`, so there is exactly one source of truth and many agent entry points.
- **Client bundle vs. theloop-only meta-skills.** Meta-skills exist to maintain theloop itself; they never ship to clients. The client gets only the user-facing workflow skills plus the minimal internal sub-skills they require.
- **`*ForClientRepos` development naming.** Skills that must differ from their theloop namesakes are developed and validated in the theloop repo under a `…ForClientRepos` suffix and **installed under the client-facing name** (`PreCommitSkillForClientRepos` → `theloop-precommit`, `ConfigureTheLoopForClientRepos` → `theloop-post-setuprepo`). The client never sees the suffix. This lets the theloop repo's own meta-validation exercise these skills without colliding with theloop's full-strength `PreCommitSkill`.

## Implementation outline

### 1. `theloopify.sh` + `theloopify` symlink (repo root)

A single bash script, phased and colorized, that instruments a target directory (cwd by default, or an explicit path argument):

1. Resolve the target directory; **refuse** if it is the theloop repo itself (detected by the canonical marker `.theloop/SKILLS-META-RULES.md`).
2. **Refuse a second run** if `.theloop/theloopified` already exists, with a "one feature per clone — clone again" message.
3. Verify the target is a git repository.
4. Detect a GitHub remote URL across all remotes (preferring a GitHub one); if none is found, **interactively prompt**; write the single-line URL to `.theloop/repo.txt`.
5. Ensure `tmp/` is present in `.gitignore` (run-receipt hygiene).
6. Create the `.theloop/` scaffolding: `do_not_commit.txt` (agreed plain paths), `must_run_configure_the_loop.txt`, and `theloopified`.
7. Copy the bundled skills from the theloop checkout's `.skills/` into the client's `.theloop/skills/`, applying the install-name renames and rewriting every `.skills/…` reference to `.theloop/skills/…` (and every `…ForClientRepos` name to its client-facing name) inside the copied files.
8. Create the four agent skill directories and, for every installed skill, a symlink from `<agent>/skills/<SkillName>` to `../../.theloop/skills/<SkillName>`.
9. Print a clean summary whose final line tells the user to run `/theloop-post-setuprepo`.

Everything is left **uncommitted**; `theloopify` never commits. The script is structured so it can later be wrapped as a Claude Code skill with minimal change (single entry point, phase functions, no hidden global state).

The mechanical copy/rewrite/rename and the integrity assertions are delegated to a Python helper, `theloopify-install.py`, which `theloopify.sh` invokes. Keeping the non-trivial logic in Python (rather than fragile `find`/`sed` pipelines) makes it testable and predictable, mirroring the repo's "use of scripts" convention.

### 2. The client bundle

| Source (theloop `.skills/`) | Installed (client `.theloop/skills/`) | Role |
|---|---|---|
| `theloop-makeissue` | `theloop-makeissue` | user-facing; configure-gated |
| `theloop-fixissue` | `theloop-fixissue` | user-facing; gated; hard-excludes `do_not_commit.txt` paths at commit |
| `theloop-buildthis` | `theloop-buildthis` | user-facing; gated; hard-excludes at commit |
| `InternalSkillCheckGhRepoAccessWithRunId` | same | sub-skill; reads `.theloop/repo.txt`, ensures `theloop` label |
| `PreCommitSkillForClientRepos` | `theloop-precommit` | user-facing; gated; slim pre-commit |
| `ConfigureTheLoopForClientRepos` | `theloop-post-setuprepo` | user-facing; one-time agentic setup |
| `InternalSkillPreCommitForClientWithRunId` | same | sub-skill; hygiene + `PRECOMMIT.md` runner |

The internal sub-skill `InternalSkillPreCommitForClientWithRunId` is included beyond the six headline skills because `PreCommitSkillForClientRepos` delegates the actual checks to it, exactly as theloop's `PreCommitSkill` delegates to `InternalSkillPreCommitSkillWithRunId`. Splitting "generate id + delegate" from "run the checks" keeps each skill to a single responsibility.

**Never installed:** `InternalSkillValidateSkill`, `InternalSkillValidateAllSkills`, `InternalSkillCheckSingleRuleWithRunId`, `InternalSkillCheckAllRulesWithRunId`, `InternalSkillPreCommitSkillWithRunId`, theloop's full `PreCommitSkill`, and the `SKILLS.md` / `.theloop/VIZ.md` / `ai-rules.yml` machinery.

### 3. `PreCommitSkillForClientRepos` → `theloop-precommit`

Parameterless entry point. Checks the configuration gate, generates a `SkillRunId`, and delegates to `InternalSkillPreCommitForClientWithRunId`. The internal sub-skill runs exactly two things:

1. **Receipt hygiene** — `tmp/` gitignored, no tracked files under `tmp/`, no staged files under `tmp/` (reusing `hygiene.py`).
2. **`PRECOMMIT.md` checks** — reads the repo-root free-form `PRECOMMIT.md` and runs the checks it describes. Because `PRECOMMIT.md` is prose (sections/bullets, not a rigid YAML schema), the runner interprets it **agentically**: for each described check it extracts the name, the directory/scope, and the command, runs it, and records the outcome. This is deliberately not cached: a check that runs the repo's tests is not determined by a fixed file set, so the caching rule does not apply.

It explicitly **excludes** theloop-only concerns: directory rules, the rules registry, and skill meta-validation.

### 4. `ConfigureTheLoopForClientRepos` → `theloop-post-setuprepo`

One-time agentic configuration. Generates its own `SkillRunId` and writes a receipt. Preconditions (enforced by `configure-preconditions.py`):

| State | `theloopified` | `must_run…txt` | `configure_the_loop.done` | `theloop-post-setuprepo` |
|---|---|---|---|---|
| fresh dev / not instrumented | absent | — | — | **refuse** (run `theloopify` first) |
| after `theloopify` | present | present | absent | **allowed** |
| already configured | present | — | present | **refuse** (already configured) |

When allowed, the agent analyzes the repo's documentation, test/lint tooling, and CI gates and writes (or extends, never blindly overwrites) a repo-root `PRECOMMIT.md` in free-form Markdown — conservatively, preferring the repo's own documented commands. On success it deletes `must_run_configure_the_loop.txt` and writes `configure_the_loop.done` (via `mark-configured.py`); on failure it leaves `must_run…txt` in place and writes no `done` marker, so the user may retry.

### 5. The configuration gate (shared, duplicated per skill)

Every user-facing workflow skill (`theloop-makeissue`, `theloop-fixissue`, `theloop-buildthis`, `theloop-precommit`) checks the gate **early**, via its own copy of `check-configured.py` (scripts are duplicated per skill, never shared, per the repo convention). The gate logic:

- `.theloop/theloopified` **absent** → not a theloopified client repo (e.g. the theloop development repo) → gate **passes** (not applicable). This keeps theloop's own use of these skills working.
- `theloopified` present and `configure_the_loop.done` present → **pass**.
- `theloopified` present and `done` absent → **fail**: tell the user to run `theloop-post-setuprepo` first, then stop.

The gate keys off the **positive** signal `configure_the_loop.done`, never the mere absence of `must_run…txt`, so deleting the pending marker cannot bypass it.

### 6. Commit hygiene (`do_not_commit.txt`)

`.theloop/do_not_commit.txt` holds plain paths (no globs): `.theloop/`, `.cursor/skills/`, `.claude/skills/`, `.codex/skills/`, `.agents/skills/`, `tmp/`. The two committing skills (`theloop-fixissue`, `theloop-buildthis`) stage via their own copy of `stage-allowed.py`, which stages all changes and then unstages every `do_not_commit.txt` path, asserting none remain staged. Feature design docs (`FEATURE.md`, `docs/<Feature>.md`) and `PRECOMMIT.md` are **not** excluded — they are user artifacts and may be committed. In the theloop repo itself, where there is no `do_not_commit.txt`, `stage-allowed.py` stages everything, matching the previous behavior.

### 7. README & registries

The README gains an end-user guide (clone → `theloopify` → `theloop-post-setuprepo` → workflow skills; what files appear and which are local-only; what `PRECOMMIT.md` is) and a short contributor section explaining the `*ForClientRepos` naming. The three new theloop-repo skills are registered in `SKILLS.md` and `.theloop/VIZ.md` (both tables and the Mermaid diagram), and a deterministic `theloopify` smoke test is added to the theloop repo's own `PRECOMMIT.md`.

## How to rebuild

If the code is lost, reconstruct it from these invariants:

1. **`theloopify.sh`** (root) + **`theloopify`** symlink → `theloopify.sh`. No arg ⇒ instrument cwd; one path arg ⇒ instrument it. Refuse when the target contains `.theloop/SKILLS-META-RULES.md` (it is the theloop repo) or already contains `.theloop/theloopified` (already instrumented). Require the target to be a git repo. Produce, all uncommitted:
   - `.theloop/repo.txt` — one GitHub URL, from remote auto-detection or an interactive prompt;
   - `tmp/` appended to `.gitignore` if absent;
   - `.theloop/do_not_commit.txt` with exactly the six plain paths above;
   - `.theloop/must_run_configure_the_loop.txt` and `.theloop/theloopified` markers;
   - `.theloop/skills/<SkillName>/` canonical copies of the seven bundled skills, with install-name renames applied and every `.skills/…` rewritten to `.theloop/skills/…` and every `…ForClientRepos` name rewritten to its client-facing name;
   - `<agent>/skills/<SkillName>` symlinks for each of `.cursor`, `.claude`, `.codex`, `.agents`, pointing at the canonical copy; **no** `.skills/` at the client root.
   The final message directs the user to `/theloop-post-setuprepo`.
2. **Bundled skills** must obey `.theloop/SKILLS-META-RULES.md` in the theloop repo: run receipts where applicable, `InternalSkill` prefix iff the skill takes `SkillRunId`, listed in `SKILLS.md` and `.theloop/VIZ.md`, scripts under each skill's own `scripts/`, and accurate `invokes:` frontmatter.
3. **The gate** is a per-skill `check-configured.py` returning pass unless the repo is theloopified-but-not-configured. **Commit exclusion** is a per-skill `stage-allowed.py` driven by `.theloop/do_not_commit.txt`. Both degrade to no-ops in a repo without the corresponding `.theloop/` files (i.e. the theloop repo).
4. **`theloop-precommit` (client)** = gate + generate id + delegate to `InternalSkillPreCommitForClientWithRunId` = hygiene + agentic `PRECOMMIT.md` checks; no rules, no skill validation.
5. **`theloop-post-setuprepo`** = preconditions (`theloopified` present, `done` absent) → agentic `PRECOMMIT.md` authoring → flip the gate (`mark-configured.py` deletes `must_run…txt`, writes `done`).
6. The whole flow upholds **one feature per clone** and **feature PRs contain only user code**.
