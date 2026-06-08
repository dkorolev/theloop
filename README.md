# `theloop`

Dima's proposal on how to use AI for cleaner code and better code reviews.

This repository describes a set of skills, compatible with Claude Code, Opencode, Cursor, etc. It also defines the rules those skills must follow, and the meta-skills that check that every skill is compliant.

If your coding agent is configured to run a skill from the command line, the skills are compatible with that. But often that mode is not configured, or is more expensive to run. So the skills are designed so you can start a new agentic shell and tell it to "Run skill …", perhaps with parameters.

## Using theloop in your own repository

theloop gives you a **discuss → issue → implement → PR** loop in your own repo, without dragging in theloop's own maintenance machinery. The core idea is **one feature per fresh clone**: you instrument a clean clone once, and that working tree is then dedicated to a single feature.

**Prerequisites:** the GitHub CLI (`gh`) installed and authenticated, a coding agent (Claude Code, Cursor, Codex, …), and a GitHub remote on your repo (or the URL ready to enter when prompted).

1. **Clone** your target repository fresh — one clone, one feature.

2. **Run `theloopify`** from your theloop checkout, pointing at the clone:

   ```sh
   /path/to/theloop/theloopify                 # instrument the current directory
   /path/to/theloop/theloopify /path/to/clone  # or instrument an explicit path
   ```

   `theloopify` is mechanical and **never commits**. It copies the skill bundle into `.theloop/skills/`, symlinks it into every supported agent directory (`.cursor/`, `.claude/`, `.codex/`, `.agents/`), writes the `.theloop/` scaffolding, detects (or asks for) your GitHub remote, and gitignores every path it instruments (the `.theloop/` scaffolding, the agent `*/skills/` symlink dirs, and `tmp/`) so none of it shows up as untracked. It refuses to run on the theloop repo itself, and refuses a second run (clone again to start another feature).

3. **Review** the uncommitted changes it produced.

4. **Run `/newrepo-theloopify-internal-postinit`** in your coding agent — required once. The agent reads your repo's docs, test/lint tooling, and CI gates and writes a repo-root **`PRECOMMIT.md`**, then marks configuration complete. Until this finishes, the other skills refuse to run.

5. **Use the workflow skills:**
   - `/theloop-makeissue` — capture a design discussion as a GitHub issue
   - `/theloop-fixissue <n>` — implement an issue and open a pull request
   - `/theloop-buildthis` — implement straight from the conversation, no issue
   - `/theloop-precommit` — run the pre-commit checks before any commit

6. **Open a PR.** The committing skills stage your changes through `.theloop/do_not_commit.txt`, so feature PRs contain **only your code** (and your feature design docs) — never the `.theloop/` scaffolding or agent symlinks.

### What lands in your repo, and what stays local

| Path | Committed in feature PRs? |
|---|---|
| `.theloop/skills/`, `.theloop/repo.txt`, `.theloop/*` markers | **No** — gitignored and listed in `.theloop/do_not_commit.txt` |
| `.cursor/skills/`, `.claude/skills/`, `.codex/skills/`, `.agents/skills/` (symlinks) | **No** — gitignored, local-only |
| `tmp/` (run receipts and caches) | **No** — gitignored |
| `.gitignore` (the entries `theloopify` adds) | **No** — modified-but-uncommitted by design (see note below) |
| `PRECOMMIT.md` | **Yes** — once written it is your file, committed as normal repo maintenance |
| Feature design documents (feature-named, e.g. under `design-docs/`) | **Yes** — they are your feature artifacts |

> **Why `.gitignore` is modified but never committed — a deliberate compromise.** `theloopify` adds every path it instruments to `.gitignore` so that none of theloop's scaffolding shows up as an untracked change; this keeps a repo that treats a dirty working tree as illegal passing its check. theloop is otherwise **not designed to alter `.gitignore`**, so it makes this one exception consciously and **never commits the change**: `.gitignore` is itself listed in `.theloop/do_not_commit.txt`, so the committing skills exclude it and the edit stays local. The accepted cost is that your working tree carries a modified-but-uncommitted `.gitignore`.

### What `PRECOMMIT.md` is

`PRECOMMIT.md` is a **free-form Markdown checklist** written by `/newrepo-theloopify-internal-postinit`, not a YAML config file. It lists your repo's pre-commit checks — tests, linters, CI gates — each with a name, where to run it, and the command. The client `theloop-precommit` skill reads it, runs the checks, and gates the commit alongside basic run-receipt hygiene. Edit it freely; it is yours.

### Supported agents

The same canonical skill copy under `.theloop/skills/` is symlinked into `.cursor/skills/`, `.claude/skills/`, `.codex/skills/`, and `.agents/skills/`, so whichever agent you use sees the same skills.

## Integration

**Claude Code:** there is a one-time, copy-and-paste terminal installer that puts the global `/newrepo-theloopify` skill on your machine. See **[SETUP-CLAUDE.md](SETUP-CLAUDE.md)** for the command and an explanation of exactly what it does. Once installed, open Claude Code in a fresh clone of your repository and run `/newrepo-theloopify` to instrument it.

## For theloop contributors

A few skills are **developed and validated in this repo under a `…ForClientRepos` name** and **installed into client repos under their client-facing name**:

| Developed here (`.skills/`) | Installed in clients as |
|---|---|
| `PreCommitSkillForClientRepos` | `theloop-precommit` |
| `ConfigureTheLoopForClientRepos` | `newrepo-theloopify-internal-postinit` |

The client never sees the `ForClientRepos` suffix — `theloopify` renames these and rewrites every `.skills/…` reference to `.theloop/skills/…` during the copy. The suffix lets these skills coexist with theloop's own full-strength `PreCommitSkill` (which stays here and is never shipped). `theloopify` also installs the internal sub-skill `InternalSkillPreCommitForClientWithRunId` that the client `theloop-precommit` skill delegates to.

The **meta-skills** (`InternalSkillValidateAllSkills`, `InternalSkillCheckAllRulesWithRunId`, `InternalSkillPreCommitSkillWithRunId`, and friends) exist to maintain theloop itself and are **never** installed into client repos; client repos get the slim workflow bundle only.

`theloopify.sh` (with the `theloopify` symlink) and its helper `theloopify-install.py` live at the repo root; `theloopify-test.sh` is a deterministic smoke test of the whole install, run as part of this repo's own pre-commit checks. `theloopify` is structured so it can later be wrapped as a Claude Code skill with minimal change.

The full feature design lives in [`FEATURE.md`](FEATURE.md).
